import os
import logging
import shutil
import time
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

# Local agent imports
from .agents.pdf_rag import PDFRAGAgent
from .agents.web_search import WebSearchAgent
from .agents.arxiv_agent import ArxivAgent

# 1. Setup Environment
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentSystemLogger")

app = FastAPI(title="Neo-Aether Multi-Agent System")

# 2. Configuration (2026 Free Tier)
MODEL_ID = "gemini-2.0-flash"
client = None


class AskRequest(BaseModel):
    query: str


class ControllerAgent:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def route_query(self, query: str) -> str:
        prompt = f"Route to: PDFRAGAgent, WebSearchAgent, ArxivAgent, or SynthesisOnly. Query: {query}. Return ONLY the name."
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Router hit a limit or error: {e}")
            return "WebSearchAgent"


# Initialize Client WITHOUT the startup ping to save your quota
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY missing in .env")

    client = genai.Client(api_key=api_key)

    # We skip the "ping" generate_content call here to prevent 429 errors
    # every time the uvicorn server reloads during development.
    logger.info(f"🚀 SYSTEM READY: Model {MODEL_ID} initialized (Ping skipped to save quota)")

    # Initialize Agents
    controller = ControllerAgent(client, MODEL_ID)
    pdf_agent = PDFRAGAgent(client, MODEL_ID)
    web_agent = WebSearchAgent(client, MODEL_ID)
    arxiv_agent = ArxivAgent(client, MODEL_ID)
except Exception as e:
    logger.critical(f"❌ Initialization Failed: {e}")
    client = None

# 3. Routes
app.mount("/frontend", StaticFiles(directory=str(PROJECT_ROOT / "frontend")), name="frontend")


@app.get("/")
async def read_index():
    return FileResponse(str(PROJECT_ROOT / "frontend" / "index.html"))


@app.post("/pdf-upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not client: raise HTTPException(status_code=503, detail="AI Offline")

    temp_dir = PROJECT_ROOT / "temp"
    temp_dir.mkdir(exist_ok=True)
    file_path = temp_dir / file.filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        success = pdf_agent.process_pdf(str(file_path))
        return {"message": "Document ingested successfully."} if success else {"message": "Processing failed."}
    finally:
        if file_path.exists():
            os.remove(file_path)


@app.post("/ask")
async def ask(request: AskRequest) -> Dict[str, str]:
    if not client:
        raise HTTPException(status_code=503, detail="AI Service Offline. Check API Key.")

    q_lower = request.query.lower()

    # 1. Deterministic Routing (Saves API calls/Quota)
    if any(k in q_lower for k in ['pdf', 'document', 'file']):
        chosen_agent = "PDFRAGAgent"
    elif any(k in q_lower for k in ['arxiv', 'paper', 'research']):
        chosen_agent = "ArxivAgent"
    else:
        # Only call the LLM to route if keywords aren't found
        chosen_agent = controller.route_query(request.query)

    display_name = chosen_agent.replace("Agent", "")

    try:
        # 2. Execution Logic
        if "PDFRAG" in chosen_agent:
            result = pdf_agent.query_pdf(request.query) if pdf_agent.index else "Please upload a PDF first."
        elif "WebSearch" in chosen_agent:
            result = web_agent.search(request.query)
        elif "Arxiv" in chosen_agent:
            result = arxiv_agent.fetch_papers(request.query)
        else:
            display_name = "Ignis (General AI)"
            resp = client.models.generate_content(model=MODEL_ID, contents=request.query)
            result = resp.text

    except Exception as e:
        if "429" in str(e):
            result = "The AI is currently busy (Rate Limit hit). Please wait 60 seconds and try again."
        else:
            logger.error(f"Execution error: {e}")
            result = f"Error: {str(e)}"

    return {"agent": display_name, "result": result}