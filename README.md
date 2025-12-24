# Agentic Team (Manual Orchestration)

This project implements a **manual agentic system** where a central **Manager Agent** coordinates multiple agents to complete software development tasks, **without using any agentic frameworks**. The system uses an LLM (via the DeepSeek API) and explicit control flow to manage task decomposition, execution, review, feedback, and documentation.

---

## 🧠 Core Idea

Given a high-level task, the system:

1. Assigns a **Manager Agent** to analyze the task
2. Breaks it into **Frontend** and **Backend** subtasks
3. Dispatches each subtask to a specialized agent
4. Sends generated code to a **Reviewer Agent**
5. Applies reviewer feedback in an iterative loop
6. Produces **technical documentation** for the both the frontned and backend

All orchestration logic is written manually, no LangChain, no CrewAI, no AutoGen.


