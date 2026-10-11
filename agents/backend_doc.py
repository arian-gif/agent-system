from utils.llm_router import LLM
from utils.codegen import generate_doc

SECTIONS = [
    ("System Overview", "purpose and scope of the backend system"),
    ("Architecture", "layers, modules and services"),
    ("Technology Stack", "language, frameworks, database, caching, messaging"),
    ("API Design", "endpoints, request and response shapes"),
    ("Data Models", "data models and database schema overview"),
    ("Authentication and Authorization", "auth strategy, or state clearly that none exists"),
    ("Error Handling and Logging", "error responses, validation and logging"),
    ("Deployment and Operations", "deployment, scaling and monitoring notes"),
    ("Design Decisions", "key design decisions and trade-offs"),
]

class BackendDocAgent:
    def __init__(self, llm_provider="deepseek", model ="deepseek-chat",code=None):
        self.llm_provider = llm_provider
        self.model = model
        self.llm = LLM(llm_provider, model)
        self.code = code

    async def generate_docs(self):
        return await generate_doc(
            self.llm,
            "Backend Technical Documentation",
            "You are a Senior Backend Engineer and Technical Writer.",
            SECTIONS,
            self.code,
        )
