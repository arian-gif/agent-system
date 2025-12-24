from pathlib import Path
import json
import shutil
import logging

# Basic logger (used by all agents)
logging.basicConfig(
    filename="workspace/logs/fs.log",
    level=logging.INFO,
    format="%(asctime)s [FS] %(message)s"
)


def ensure_dir(path: Path):
    """
    Ensure a directory exists.
    """
    path.mkdir(parents=True, exist_ok=True)


def safe_write_file(path: Path, content: str):
    """
    Safely write content to a file.
    - Creates parent directories automatically
    - Overwrites existing file
    - Uses UTF-8 encoding
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    logging.info(f"Wrote file: {path}")


def safe_read_file(path: Path) -> str:
    """
    Safely read a file.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: dict):
    """
    Write JSON data safely.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logging.info(f"Wrote JSON: {path}")


def read_json(path: Path) -> dict:
    """
    Read JSON safely.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist")
    return json.loads(path.read_text(encoding="utf-8"))


def copy_tree(src: Path, dst: Path):
    """
    Copy directory tree safely.
    """
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    logging.info(f"Copied {src} -> {dst}")
