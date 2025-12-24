from fastapi import FastAPI, File, UploadFile, Form,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import docx
from io import BytesIO
from typing import Optional
from manager.manager import ManagerAgent
import uvicorn


app = FastAPI(title="Agent Orchestrator Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from .docx file"""
    try:
        doc = docx.Document(BytesIO(file_content))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        return f"Error reading file: {str(e)}"


@app.post("/api/generate")
async def generate_code(file: Optional[UploadFile] = File(None),description: str = Form(...)):
    task = None
    if file:
        content = await file.read()
        if len(content) > 5000000:
            raise HTTPException(status_code=413, detail="File too large")

        if file.filename.endswith('.docx'):
            task = extract_text_from_docx(content)
        else:
            task = content.decode('utf-8', errors='ignore')
        task += f"\n {description}"
    else:
        task = description
    manager = ManagerAgent(task)
    try:
        result = await manager.run_manager()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"error:{e}")
    return {
        "status": "success",
        "result": result
    }



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)

