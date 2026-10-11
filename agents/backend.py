from utils.llm_router import LLM
from utils.codegen import generate_project, fix_project

class BackendAgent:
    def __init__(self, llm_provider="deepseek", model ="deepseek-chat",specs=None):
        self.llm_provider = llm_provider
        self.model = model
        self.llm = LLM(llm_provider, model)
        self.specs = specs

    async def generate_code(self):
        return await generate_project(self.llm, self.system_prompt(), self.specs, root="backend")

    def system_prompt(self)->str:
        return """
        You are the Backend Engineer Agent.
        Your task is to generate a backend service as described in the specification.

        RULES:
        - Use FastAPI (preferred) or Express only if asked.
        - SQL schema is for reference ONLY.
        - DO NOT output SQL.
        - DO NOT include explanations or comments.
        - Include proper error handling.
        - Follow clean architecture principles.
        - Put all backend files under a backend/ directory.
        - Routers declare their FULL path prefix themselves (e.g.
          APIRouter(prefix="/api/notes")); main.py calls include_router(router)
          with NO extra prefix, so paths are not doubled (never /api/api/...).
        - Return errors as FastAPI's standard {"detail": "<message>"} body.
        - Use absolute imports rooted at the app package (from app.x import y).
        """

    async def fix_code(self, review_report: list, code)->dict:
        return await fix_project(self.llm, self.system_prompt(), self.specs, code, review_report)
