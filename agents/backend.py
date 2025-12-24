from utils.llm_router import LLM
import json

class BackendAgent:
    def __init__(self, llm_provider="deepseek", model ="deepseek-chat",specs=None):
        self.llm_provider = llm_provider
        self.model = model
        self.llm = LLM(llm_provider, model)
        self.specs = specs

    async def generate_code(self):
        prompt = self.system_prompt()
        response = await self.llm.chat(prompt)
        try:
            result = json.loads(response)
        except:
            raise ValueError("BackendAgent returned invalid JSON during code generation.")
        
        return result

    def system_prompt(self)->str:
        return f"""
        You are a backend developer. You are given the following specifications:You are the Backend Engineer Agent.
        Your task is to generate a backend service as described in the specification.

        RULES:
        - Use FastAPI (preferred) or Express only if asked.
        - SQL schema is for reference ONLY.
        - DO NOT output SQL, markdown, or code blocks.
        - DO NOT include explanations or comments.
        - OUTPUT MUST BE VALID JSON ONLY.
        - Include proper error handling.
        - Follow clean architecture principles.
        - DO NOT include explanations. Only return the JSON response.

        SPECIFICATION:
        {self.specs}
        OUTPUT FORMAT (MANDATORY):
        {{
          "files": [
            {{"path": "backend/app/main.py", "content": "import fastapi..."}},
            {{"path": "backend/app/routes/example.py", "content": "..."}}
          ]
        }}

        Only return valid JSON.

        """

    async def fix_code(self, review_report: dict, code)->dict:
        system_prompt = self.system_prompt()
            
        prompt = f"""
        {system_prompt}
        The reviewer found issues in your backend code.
        Fix the backend code accordingly.

        SPEC:
        {self.specs}

        Code:
        {code}

        Review Report:
        {review_report}
        """
        response = await self.llm.chat(prompt)
        try:
            result = json.loads(response)
        except:
            raise ValueError("BackendAgent returned invalid JSON during fix cycle.")
        
        
        return result