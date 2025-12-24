from utils.llm_router import LLM
import json

class BackendDocAgent:
    def __init__(self, llm_provider="deepseek", model ="deepseek-chat",code=None):
        self.llm_provider = llm_provider
        self.model = model
        self.llm = LLM(llm_provider, model)
        self.code = code

    async def generate_docs(self):
        prompt = self.system_prompt()
        response = await self.llm.chat(prompt)

        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            raise ValueError("BackendAgent returned invalid JSON.")

        return result

    def system_prompt(self) -> str:
        return f"""
        You are a Senior Backend Engineer and Technical Writer.

        Your task is to produce **formal technical documentation** for a backend system.

        RULES:
        - This is NOT a code generation task.
        - Write in a professional, technical tone.
        - Be concise, structured, and implementation-focused.
        - Do NOT include markdown.
        - Do NOT include explanations outside the JSON.
        - Output MUST be valid JSON.
        - Do NOT wrap the response in backticks.

        DOCUMENTATION SHOULD INCLUDE:
        - System overview
        - Architecture description (layers, modules, services)
        - Technology stack (language, frameworks, database, caching, messaging, etc.)
        - API design and endpoints
        - Data models and database schema overview
        - Authentication and authorization strategies
        - Error handling and logging
        - Deployment, scaling, and monitoring notes
        - Key design decisions and trade-offs

        OUTPUT FORMAT (MANDATORY):
        {{
        "title": "Backend Technical Documentation",
        "sections": [
            {{
            "heading": "System Overview",
            "content": [
                "Paragraph 1",
                "Paragraph 2"
            ]
            }},
            {{
            "heading": "Architecture",
            "content": [
                "Paragraph 1"
            ]
            }}
        ]
        }}


        Only return valid JSON.
        """
