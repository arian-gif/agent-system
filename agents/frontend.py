from utils.llm_router import LLM
import json

class FrontendAgent:
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
            raise ValueError("FrontendAgent returned invalid JSON during code generation.")
        
        return result

    def system_prompt(self) -> str:
        return f"""
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
        - Do NOT include explanations, comments outside code, or markdown.
        - Only output the requested files.
        - Output MUST be valid JSON.
        - Do NOT wrap the response in triple backticks.
        - Do NOT include any text before or after the JSON.
        - If the implementation would exceed a reasonable file size, simplify the solution instead of adding features.
        -DO NOT EXCEED 1000 words in the JSON no matter what, even if you need to fix something, find work arounds, THIS IS A MVP


        SPECIFICATION:
        {self.specs}

        OUTPUT FORMAT (MANDATORY):
        {{
        "files": [
            {{
            "path": "frontend/src/main.tsx",
            "content": "import React from 'react'..."
            }},
            {{
            "path": "frontend/src/App.tsx",
            "content": "export default function App() {{ ... }}"
            }}
        ]
        }}

        Only return valid JSON.
        """

    async def fix_code(self, review_report: dict,code)->dict:
        system_prompt = self.system_prompt()
            
        prompt = f"""
        {system_prompt}
        The reviewer found issues in your frontend code.
        Fix the frontend code accordingly.

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
