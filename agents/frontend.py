from utils.llm_router import LLM
from utils.codegen import generate_project, fix_project

class FrontendAgent:
    def __init__(self, llm_provider="deepseek", model ="deepseek-chat",specs=None):
        self.llm_provider = llm_provider
        self.model = model
        self.llm = LLM(llm_provider, model)
        self.specs = specs

    async def generate_code(self):
        return await generate_project(self.llm, self.system_prompt(), self.specs, root="frontend")

    def system_prompt(self) -> str:
        return """
        You are the Frontend Engineer Agent.

        Your task is to generate a frontend application based on the given specification.

        RULES:
        - Implement ONLY a minimal UI required to verify API integration.
        - Use a single page with basic form inputs and simple lists.
        - Do NOT include charts, dialogs, modals, tabs, or advanced UI components.
        - Avoid third-party visualization libraries (e.g., recharts).
        - Prefer plain JSX + basic layout over UI-heavy abstractions.
        - Use React with TypeScript unless otherwise specified.
        - Prefer modern tools (Vite, React hooks, functional components).
        - Use clean, readable, production-quality code.
        - Organize code into components, pages, services, and utilities where appropriate.
        - Do NOT include backend code.
        - Put all frontend files under a frontend/ directory.
        - Call the API at the exact paths given in the specification's API
          contracts (including the /api prefix); do not add any other prefix.
        - Backend errors arrive as {"detail": "<message>"}; show that text.
        """

    async def fix_code(self, review_report: list, code)->dict:
        return await fix_project(self.llm, self.system_prompt(), self.specs, code, review_report)
