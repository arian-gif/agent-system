from utils.llm_router import LLM
from utils.codegen import generate_doc

SECTIONS = [
    ("System Overview", "purpose and scope of the frontend application"),
    ("Architecture", "overall architecture and main building blocks"),
    ("Technology Stack", "language, framework, build tooling and libraries"),
    ("Application Structure", "directory layout, components, pages and services"),
    ("State Management", "state management strategy"),
    ("Routing", "routing strategy, or state clearly that it is single-page"),
    ("Build and Deployment", "build and deployment notes"),
    ("Design Decisions", "key design decisions and trade-offs"),
]

class FrontendDocAgent:
    def __init__(self, llm_provider="deepseek", model ="deepseek-chat",code=None):
        self.llm_provider = llm_provider
        self.model = model
        self.llm = LLM(llm_provider, model)
        self.code = code

    async def generate_docs(self):
        return await generate_doc(
            self.llm,
            "Frontend Technical Documentation",
            "You are a Senior Frontend Engineer and Technical Writer.",
            SECTIONS,
            self.code,
        )
