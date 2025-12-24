from utils.llm_router import LLM
import json
import json

class ReviewerAgent:
    def __init__(self, llm_provider="deepseek", model ="deepseek-chat",code=None):
        self.llm_provider = llm_provider
        self.model = model
        self.llm = LLM(llm_provider, model)
        self.code_content = code
    
    async def review(self):
        files = self.code_content["files"]
        review = {
            "files": []
        }
        for file in files:
            path = file["path"]
            content = file["content"]
            prompt = self.system_prompt(content,path)
            llm_response = await self.llm.chat(prompt)
            if isinstance(llm_response, str):
                llm_response = json.loads(llm_response)

            review["files"].append(llm_response)
        
        return review

    def system_prompt(self, code: str,path: str) -> str:
        return f"""
            You are a strict code reviewer.

            You will review EXACTLY ONE source file.

            RULES:
            - Review only the code provided.
            - Do NOT reference other files or project context.
            - Return ONLY valid JSON.
            - Do NOT include explanations, markdown, or extra text.

            OUTPUT FORMAT:
            Return a single JSON object representing the review result for this file.

            The object MUST contain:
            - "path": string (file path)
            - "status": "pass" or "fail"
            - "issues": array of issue objects

            Each issue object MUST contain:
            - "type": "review"
            - "message": concise description of the issue
            - "line": integer (1-based) or null if unknown
            - "severity": defines how severe the issue

            If no issues are found, return an empty issues array.

            SEVERITY RULES:
            - critical: causes runtime error, crash, data loss, security issue, or incorrect behavior
            - major: likely bug or incorrect behavior in edge cases
            - minor: style issues, best practices, deprecations, readability

            STATUS RULES:
            - status MUST be "fail" if and only if at least one issue has severity "critical"
            - otherwise status MUST be "pass"

            CODE (path: "{path}"):
            {code}

            VALID OUTPUT EXAMPLE:
            {{
            "path": "{path}",
            "status": "pass",
            "issues": []
            }}

            IMPORTANT:
            - Output MUST be valid JSON.
            - Do NOT stringify JSON.
            - Do NOT escape quotes.
        """
