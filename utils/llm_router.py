from openai import OpenAI
from dotenv import load_dotenv
import os
import re
import asyncio

load_dotenv()

MAX_CONTINUATIONS = 4
CONTINUE_PROMPT = (
    "Your previous reply was cut off by the output limit. Continue exactly "
    "where you stopped. Output only the remaining text, with no repetition, "
    "no preamble and no code fences."
)

# Largest output the provider allows per request; None = provider default.
MAX_OUTPUT_TOKENS = {
    "deepseek": 8192,  # deepseek-chat defaults to 4096 unless raised
}

class LLM:
    def __init__(self, provider, model) -> None:
        self.provider = provider
        self.model = model
        self.max_tokens = MAX_OUTPUT_TOKENS.get(provider)

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

    def complete(self, prompt):
        """
        Run a completion and, if the model hit the output token limit
        (finish_reason == "length"), ask it to continue and stitch the
        pieces together so a long answer is not silently truncated.
        """
        messages = [{"role": "system", "content": prompt}]
        kwargs = {}
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        parts = []
        for _ in range(MAX_CONTINUATIONS + 1):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            choice = response.choices[0]
            text = choice.message.content or ""
            parts.append(text)

            if choice.finish_reason != "length":
                return "".join(parts)

            messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": CONTINUE_PROMPT},
            ]

        raise ValueError(
            f"LLM output still truncated after {MAX_CONTINUATIONS} continuations"
        )

    def json_response(self, prompt):
        return self.extract_json(self.complete(prompt))

    def normal_response(self, prompt):
        return self.complete(prompt)

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
    

        

        