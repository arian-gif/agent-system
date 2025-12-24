from openai import OpenAI
from dotenv import load_dotenv
import os
import re
import asyncio

load_dotenv()

class LLM:
    def __init__(self, provider, model) -> None:
        self.provider = provider
        self.model = model

        if provider == "deepseek":
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            self.base_url = "https://api.deepseek.com"
        elif provider =="groq":
            self.api_key = os.getenv("GROQ_API_KEY")
            self.base_url = "https://api.groq.com/openai/v1"
        elif provider=="gemini":
            self.api_key = os.getenv("GEMINI_API_KEY")
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        else:
            raise Exception("Invalid provider selected.")

        self.client= OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    async def chat(self, prompt, type="json"):
        loop = asyncio.get_running_loop()

        if type =="json":
            return await loop.run_in_executor(
                None,
                self.json_response,
                prompt
            )
        else:
            return await loop.run_in_executor(
                None,
                self.normal_response,
                prompt
            )

    def json_response(self, prompt):
        messages = [{"role": "system", "content": prompt}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return self.extract_json(response.choices[0].message.content)

    def normal_response(self, prompt):
        messages = [{"role": "system", "content": prompt}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content

    def extract_json(self, text):
        text = text.strip()

        # Remove ```json or ``` at the start
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)

        # Remove ``` at the end
        text = re.sub(r"\n?```$", "", text)

        # Now extract the JSON object itself
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object found in LLM response")

        return match.group(0)
    

        

        