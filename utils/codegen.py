import ast
import asyncio
import json
import re

MAX_CONCURRENCY = 4
MAX_PLANNED_FILES = 15


def strip_fences(text: str) -> str:
    """Remove a wrapping ```lang ... ``` fence if the model added one."""
    text = text.strip()
    # DeepSeek occasionally leaks its tool-call markup (</｜DSML｜...>) into output
    text = re.sub(r"</?\s*[｜|]+\s*DSML\s*[｜|]+[^>\n]*>", "", text)
    # ...and sometimes wraps the file in pseudo-XML such as <final_file>
    text = re.sub(r"^\s*</?(?:final_file|file|content|code|answer|output|result)\b[^>\n]*>\s*", "", text)
    text = re.sub(r"\s*</?(?:final_file|file|content|code|answer|output|result)\b[^>\n]*>\s*$", "", text)
    text = re.sub(r"^```[a-zA-Z0-9_+-]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text


async def gather_limited(coros):
    """Run coroutines concurrently, at most MAX_CONCURRENCY at a time."""
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def run(coro):
        async with sem:
            return await coro

    return await asyncio.gather(*(run(c) for c in coros))


def format_plan(plan: list) -> str:
    return "\n".join(
        f"- {f['path']}: {f.get('purpose', '')} | exports/interfaces: {f.get('exports', '')}"
        for f in plan
    )


async def plan_files(llm, rules: str, specs: str, root: str = None) -> list:
    """
    Step 1: ask for a small manifest (path + purpose + exports per file)
    instead of the whole project, so this call is always short.
    """
    prompt = f"""
    {rules}

    SPECIFICATION:
    {specs}

    Do NOT write any code yet. Plan the project files only.
    - List at most {MAX_PLANNED_FILES} files, only those needed for the MVP.
    - For each file give its path, a one-sentence purpose, and "exports":
      the EXACT identifiers it defines for other files to import
      (functions with signatures, classes, components, types, constants).
      This is a binding contract: files are written independently, so any
      name another file needs MUST be listed here, spelled exactly.
    - Also give "depends_on": the paths of the OTHER planned files this file
      imports or calls (empty list if none). Files are written in dependency
      order and see the real source of what they depend on.
    - Output MUST be valid JSON only, no markdown.

    OUTPUT FORMAT (MANDATORY):
    {{
      "files": [
        {{"path": "app/models.py", "purpose": "...", "exports": "...", "depends_on": []}},
        {{"path": "app/main.py", "purpose": "...", "exports": "...", "depends_on": ["app/models.py"]}}
      ]
    }}
    """
    raw = await llm.chat(prompt)
    try:
        plan = json.loads(raw)["files"]
        if not plan or not all("path" in f for f in plan):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise ValueError("Planner returned an invalid file manifest.")
    plan = plan[:MAX_PLANNED_FILES]

    def norm(p):
        # the model doesn't reliably keep the requested top-level folder
        p = p.removeprefix("./").lstrip("/")
        return p if not root or p.startswith(root + "/") else f"{root}/{p}"

    for f in plan:
        f["path"] = norm(f["path"])
    known = {f["path"] for f in plan}
    for f in plan:
        deps = f.get("depends_on") or []
        if not isinstance(deps, list):
            deps = []
        f["depends_on"] = [d for d in map(norm, deps) if d in known and d != f["path"]]
    return plan


def dependency_waves(plan: list) -> list:
    """Group files so every file comes after the files it depends on."""
    done, waves, remaining = set(), [], list(plan)
    while remaining:
        wave = [f for f in remaining if all(d in done for d in f["depends_on"])]
        if not wave:  # dependency cycle: write the rest together
            wave = remaining
        waves.append(wave)
        done.update(f["path"] for f in wave)
        remaining = [f for f in remaining if f not in wave]
    return waves


CODE_EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".css")
_LONE_TAG = re.compile(r"^\s*</?[A-Za-z_｜|][^>\n]*>\s*$")


def strip_stray_tags(path: str, text: str) -> str:
    """
    Models sometimes leave a lone pseudo-XML tag (</invoke>, </interface>,
    <final_file>) as the first or last line of a file. In a code file that
    is never valid (files end with code, not a tag), so drop it.
    """
    if not path.endswith(CODE_EXTS):
        return text
    lines = text.strip().split("\n")
    while lines and _LONE_TAG.match(lines[-1]):
        lines.pop()
    while lines and _LONE_TAG.match(lines[0]):
        lines.pop(0)
    return "\n".join(lines)


async def write_file(llm, rules: str, specs: str, plan: list, entry: dict,
                     existing: str = None, issues=None, context: dict = None) -> dict:
    """
    Step 2: one LLM call that produces the raw contents of ONE file.
    With `existing` and `issues` it rewrites that file to fix the review.
    `context` maps path -> source of already-written files this one uses.
    """
    context_block = ""
    if context:
        context_block = "ACTUAL SOURCE of the project files this file uses. Use their " \
            "real class, function, method, attribute and field names EXACTLY; " \
            "never assume something they do not define:\n" + "\n".join(
                f"--- {p} ---\n{src}\n" for p, src in context.items())
    task = f"Write the complete contents of the file: {entry['path']}"
    if existing is not None:
        task = (
            f"Rewrite the complete contents of the file: {entry['path']}\n"
            f"The reviewer found these issues, fix them:\n{issues}\n\n"
            f"CURRENT FILE CONTENT:\n{existing}"
        )

    prompt = f"""
    {rules}

    SPECIFICATION:
    {specs}

    PROJECT FILE PLAN (all files in the project):
    {format_plan(plan)}

    {context_block}

    THIS FILE: {entry['path']} - {entry.get('purpose', '')}

    {task}

    OUTPUT RULES:
    - Output ONLY the raw file content.
    - No markdown, no code fences, no explanations.
    - This file MUST define every name listed in its own exports above.
    - Import from other project files ONLY names listed in that file's
      exports in the plan; never invent or rename them.
    """
    text = await llm.chat(prompt, type="md")
    return {"path": entry["path"],
            "content": strip_stray_tags(entry["path"], strip_fences(text))}


def _module_names(path: str) -> list:
    """All dotted names a project file could be imported as."""
    parts = path[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return [".".join(parts[i:]) for i in range(len(parts))] if parts else []


def check_python_imports(files: list) -> list:
    """
    Cheap static check: every `from <project module> import name` must name
    something that module defines. Returns review-style entries for the
    files that import a missing name.
    """
    py = {f["path"]: f["content"] for f in files if f["path"].endswith(".py")}
    defined, modules = {}, {}
    for path, src in py.items():
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        names = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names.update(t.id for t in targets if isinstance(t, ast.Name))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names.update((a.asname or a.name).split(".")[0] for a in node.names)
        defined[path] = names
        for m in _module_names(path):
            modules.setdefault(m, path)

    report = []
    for path, src in py.items():
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        pkg = path.split("/")[:-1]
        issues = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level:
                base = pkg[: len(pkg) - (node.level - 1)]
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            target = modules.get(mod)
            if not target:
                continue
            for a in node.names:
                if a.name != "*" and a.name not in defined[target] \
                        and not modules.get(f"{mod}.{a.name}"):
                    issues.append(
                        f"imports '{a.name}' from {target}, which does not define it "
                        f"(it defines: {', '.join(sorted(defined[target]))}). "
                        f"Change THIS file to import and use only names that exist there."
                    )
        if issues:
            report.append({"path": path, "status": "fail", "issues": issues})
    return report


async def generate_project(llm, rules: str, specs: str, root: str = None) -> dict:
    plan = await plan_files(llm, rules, specs, root)

    # Dependency order: each wave runs in parallel, but sees the real source
    # of the earlier files it depends on, so names/methods line up.
    written = {}
    for wave in dependency_waves(plan):
        results = await gather_limited([
            write_file(llm, rules, specs, plan, entry,
                       context={d: written[d] for d in entry["depends_on"] if d in written})
            for entry in wave
        ])
        written.update({r["path"]: r["content"] for r in results})

    code = {"files": [{"path": e["path"], "content": written[e["path"]]} for e in plan]}
    return await repair_imports(llm, rules, specs, code, plan)


async def repair_imports(llm, rules: str, specs: str, code: dict, plan: list = None,
                         rounds: int = 2) -> dict:
    """Rewrite files whose cross-file imports don't resolve (bounded rounds)."""
    for _ in range(rounds):
        broken = check_python_imports(code["files"])
        if not broken:
            break
        code = await fix_project(llm, rules, specs, code, broken, plan=plan, recheck=False)
    return code


async def fix_project(llm, rules: str, specs: str, code: dict, review: list,
                      plan: list = None, recheck: bool = True) -> dict:
    """Regenerate only the files the reviewer failed; keep the rest as is."""
    failed = {r["path"]: r.get("issues", []) for r in review if r.get("status") == "fail"}
    plan = plan or [{"path": f["path"]} for f in code["files"]]
    entries = {e["path"]: e for e in plan}

    async def fix(f):
        if f["path"] not in failed:
            return f
        # show the rewrite the current source of the other files (bounded)
        others = {"files": [g for g in code["files"] if g["path"] != f["path"]]}
        context = {g["path"]: g["content"][:6000] for g in others["files"]}
        used, bounded = 0, {}
        for p, src in context.items():
            if used + len(src) > 40000:
                break
            bounded[p] = src
            used += len(src)
        return await write_file(
            llm, rules, specs, plan, entries.get(f["path"], {"path": f["path"]}),
            existing=f["content"], issues=failed[f["path"]], context=bounded,
        )

    fixed = {"files": list(await gather_limited([fix(f) for f in code["files"]]))}
    if recheck:
        # a rewrite can introduce new broken imports; verify before returning
        fixed = await repair_imports(llm, rules, specs, fixed, plan)
    return fixed


def code_digest(code: dict, per_file: int = 6000, total: int = 60000) -> str:
    """Bounded text view of the generated code, for doc prompts."""
    out, used = [], 0
    for f in (code or {}).get("files", []):
        chunk = f"--- {f['path']} ---\n{f['content'][:per_file]}\n"
        if used + len(chunk) > total:
            out.append(f"--- {f['path']} --- (omitted, size limit)\n")
            continue
        out.append(chunk)
        used += len(chunk)
    return "\n".join(out)


async def generate_doc(llm, title: str, role: str, sections: list, code: dict) -> dict:
    """One short call per section instead of one giant document."""
    digest = code_digest(code)

    async def section(heading, guidance):
        prompt = f"""
        {role}

        Write ONE section of formal technical documentation: "{heading}".
        Cover: {guidance}

        RULES:
        - Professional, concise, implementation-focused.
        - Base it on the code below; do not invent features it lacks.
        - Output plain paragraphs separated by a blank line.
        - No markdown, no headings, no bullet syntax, no code fences.

        CODE:
        {digest}
        """
        text = await llm.chat(prompt, type="md")
        paras = [p.strip() for p in strip_fences(text).split("\n\n") if p.strip()]
        return {"heading": heading, "content": paras}

    results = await gather_limited([section(h, g) for h, g in sections])
    return {"title": title, "sections": list(results)}
