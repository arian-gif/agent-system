import json
from utils.llm_router import LLM
from agents.backend import BackendAgent
from agents.frontend import FrontendAgent
from agents.reviewer import ReviewerAgent
from agents.frontend_doc import FrontendDocAgent
from agents.backend_doc import BackendDocAgent
import asyncio

class ManagerAgent:
    def __init__(self, task, llm_provider="deepseek", model ="deepseek-chat"):
        self.task = task
        self.llm_provider = llm_provider
        self.model = model
        self.llm = LLM(llm_provider, model)
    
    async def call_frontend_agent(self,specs, review = False, review_dict = {},code={}):
        agent = FrontendAgent(specs=specs)
        if not review:
            return await agent.generate_code()
        return await agent.fix_code(review_report=review_dict,code=code)
    
    async def call_backend_agent(self,specs, review = False, review_dict = {},code = {}):
        agent = BackendAgent(specs=specs)
        if not review:
            
            return await agent.generate_code()
        return await agent.fix_code(review_report=review_dict,code = code)
    
    async def call_reviewer_agent(self,code):
        agent = ReviewerAgent(code =code)
        return await agent.review()

    async def generate_specs(self, agent_type):
        
        prompt = f"""
            You are the Manager Agent.

            Your responsibility is to generate a **SPECIFICATION CARD** for the {agent_type.upper()} agent.
            This spec will be used by an autonomous agent to generate production code.

            TASK CONTEXT:
            {self.task}

            GENERAL RULES:
            - This specification must describe a MINIMUM VIABLE PRODUCT (MVP) only.
            - Exclude advanced analytics, charts, dialogs, modals, tabs, or complex UI flows.
            - Prefer the smallest feature set that satisfies core functionality.
            - Assume a single-page implementation unless otherwise required.
            - This document is a technical specification, NOT code.
            - Do NOT include SQL, migrations, database queries, or persistence details.
            - Do NOT include markdown code blocks (no ```).
            - Do NOT include explanations or commentary.
            - Be concise, unambiguous, and implementation-ready.
            - Use markdown headers and bullet points only.
            - Assume the agent has no additional context beyond this spec.

            AGENT-SPECIFIC RULES:
            {"- Focus ONLY on backend concerns (APIs, models, validation, services, error handling)." if agent_type == "backend" else ""}
            {"- Focus ONLY on frontend concerns (UI, state management, API consumption, UX states)." if agent_type == "frontend" else ""}
            - Do NOT reference the other agent's implementation details.
            - Clearly define integration contracts where applicable.

            IMPORTANT: The specification must follow this EXACT format and structure:

            ## Overview
            [Brief system description]

            ## Functional Requirements
            - [Bullet point requirement 1]
            - [Bullet point requirement 2]

            ## Data Models
            - This section defines **in-memory or runtime objects only**, no database or persistence.
            - Use bullets with `field: type`, one field per line.
            - Do NOT use curly braces or JSON syntax.
            - Example:
                - TrackedItem
                    - id: string
                    - name: string
                    - description: string
                    - currentValue: number
                    - createdAt: datetime
                    - updatedAt: datetime
                - ValueHistory
                    - id: string
                    - itemId: string
                    - previousValue: number
                    - delta: number
                    - newValue: number
                    - note: string
                    - timestamp: datetime

            ## API Contracts
            - List endpoints exactly as specified.
            - For each endpoint, use this format:
                - HTTP_METHOD /api/endpoint
                - Request:
                    - field_name: type
                    - field_name: type
                - Response:
                    - field_name: type
                    - field_name: type
            - Do NOT use curly braces, JSON, or code-like syntax.
            - Example:
                - POST /api/items
                - Request:
                    - name: string
                    - description: string
                    - currentValue: number
                - Response:
                    - id: string
                    - name: string
                    - description: string
                    - currentValue: number
                    - createdAt: datetime
                    - updatedAt: datetime

            ## Error Handling
            - Status code for specific error condition
            - Status code for another error condition

            ## Output Expectations
            - [Expected implementation detail 1]
            - [Expected implementation detail 2]

            REQUIRED FOR BACKEND:
            - Include these exact API endpoints:
                - POST /api/items
                - GET /api/items
                - GET /api/items/{id}
                - POST /api/items/{id}/change
                - GET /api/items/{id}/history
                - DELETE /api/items/{id}
            - Include these exact data models: TrackedItem and ValueHistory
            - TrackedItem must have: id, name, description, currentValue, createdAt, updatedAt
            - ValueHistory must have: id, itemId, previousValue, delta, newValue, note, timestamp

            SCOPE LIMITATION:
            - The goal is correctness and integration, NOT completeness.
            - If a feature is not strictly required for core functionality, exclude it.


            FINAL RULE:
            This spec must be sufficient for the {agent_type} agent to implement the system without assumptions.
            Output ONLY the specification in the exact format above, nothing else.
        """

        result = await self.llm.chat(prompt,type="md")


        # Ensure string output
        if not isinstance(result, str):
            result = json.dumps(result, indent=2)

        return result

    def approve(self,feedback):
        files = feedback["files"]

        for file in files:
            if file["status"] == "fail":
                return False
        
        return True
    
    async def feedback_loop(self,code,agent_type,specs):
        max_revisions = 3
        revision_count =0

        while True:
            review = await self.call_reviewer_agent(code)
            approval = self.approve(review)

            if approval:
                return code
            
            if revision_count >= max_revisions:
                raise Exception("Max revisions exceeded")
            
            if agent_type == "backend":
                code = await self.call_backend_agent(
                specs,
                review=True,
                review_dict=review["files"],
                code = code
            )
            elif agent_type == "frontend":
                code= await self.call_frontend_agent(
                specs,
                review=True,
                review_dict=review["files"],
                code=code
            )
            revision_count +=1

    async def run_backend(self):
        specs = await self.generate_specs("backend")
        backend_code = await self.call_backend_agent(specs)
        result = await self.feedback_loop(backend_code,"backend",specs)
        return result

    async def run_frontend(self):
        specs = await self.generate_specs("frontend")
        frontend_code = await self.call_frontend_agent(specs)
        result = await self.feedback_loop(frontend_code,"frontend",specs)
        return result

    async def run_frontend_doc(self,frontend_code):
        agent = FrontendDocAgent(code=frontend_code)
        frontend_doc = await agent.generate_docs()

        return frontend_doc
    
    async def run_backend_doc(self,backend_code):
        agent = BackendDocAgent(code=backend_code)
        backend_doc = await agent.generate_docs()

        return backend_doc


    async def run_manager(self):
        backend_task = asyncio.create_task(self.run_backend())
        frontend_task = asyncio.create_task(self.run_frontend())

        backend_code, frontend_code = await asyncio.gather(
            backend_task,
            frontend_task
        )
        backend_doc_task = asyncio.create_task(self.run_backend_doc(backend_code))
        frontend_doc_task = asyncio.create_task(self.run_frontend_doc(frontend_code))

        backend_doc, frontend_doc = await asyncio.gather(
            backend_doc_task,
            frontend_doc_task
        )

        return {
            "backendCode": backend_code,
            "frontendCode": frontend_code,
            "backendDoc": backend_doc,
            "frontendDoc": frontend_doc,
        }

if __name__ == "__main__":
    task_description = f"""
        Build a minimal full-stack note-taking app.
        """


    manager = ManagerAgent(task_description)
    result = asyncio.run(manager.run_manager())
    for key, value in result.items():
        print(f"{key}:{value}")
        