import os
import logging
import shutil
import asyncio
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
# resolve().parent.parent ensures we find the root even when running from 'app'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv()  # Load local .env if it exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentSystemLogger")

app = FastAPI(title="Neo-Aether Multi-Agent System")

# 2. Configuration (2026 Free Tier)
MODEL_ID = "gemini-2.5-flash"
client = None


class AskRequest(BaseModel):
    query: str


class ControllerAgent:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def route_query(self, query: str) -> str:
        """Intelligent routing fallback using LLM."""
        prompt = f"""
        Analyze the user query and pick the best agent:
        - "PDFRAGAgent": Use for document analysis, summaries, or resume questions.
        - "WebSearchAgent": Use for general knowledge or current events.
        - "ArxivAgent": Use for academic papers or research queries.

        Return ONLY the name.
        Query: "{query}"
        """
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            name = response.text.strip().replace("`", "").replace('"', '')
            # Ensure return is a valid agent name for the logic below
            if "PDF" in name: return "PDFRAGAgent"
            if "Arxiv" in name: return "ArxivAgent"
            return "WebSearchAgent"
        except Exception:
            return "WebSearchAgent"


# Initialize Global Components
try:
    # Prioritize Environment Variables (Render) over .env
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")

    client = genai.Client(api_key=api_key)

    # Initialize Agents
    controller = ControllerAgent(client, MODEL_ID)
    pdf_agent = PDFRAGAgent(client, MODEL_ID)
    web_agent = WebSearchAgent(client, MODEL_ID)
    arxiv_agent = ArxivAgent(client, MODEL_ID)

    logger.info(f"🚀 SYSTEM READY: Model {MODEL_ID} initialized")
except Exception as e:
    logger.critical(f"❌ Initialization Failed: {e}")
    client = None

# 3. Routes & Static Files
# Mount the frontend directory so HTML/JS/CSS are accessible
app.mount("/frontend", StaticFiles(directory=str(PROJECT_ROOT / "frontend")), name="frontend")


@app.get("/")
async def read_index():
    # Serves the main entry point of your cinematic portal
    return FileResponse(str(PROJECT_ROOT / "frontend" / "index.html"))


@app.post("/pdf-upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not client: raise HTTPException(status_code=503, detail="AI Offline")

    # Use /tmp for Render compatibility as it is usually the only writable directory
    temp_dir = Path("/tmp") if os.name != "nt" else PROJECT_ROOT / "temp"
    temp_dir.mkdir(exist_ok=True)
    file_path = temp_dir / file.filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        success = pdf_agent.process_pdf(str(file_path))
        return {"message": "Document ingested successfully." if success else "Failed to index PDF."}
    finally:
        if file_path.exists(): os.remove(file_path)


@app.post("/ask")
async def ask(request: AskRequest) -> Dict[str, str]:
    if not client:
        raise HTTPException(status_code=503, detail="AI Service Offline.")

    # Artificial delay to prevent API rate-limiting on free tier
    await asyncio.sleep(1.2)

    q_lower = request.query.lower()

    # 1. Deterministic Routing (Mandatory Keyword Check)
    if any(k in q_lower for k in ['pdf', 'summarize', 'document', 'resume', 'sentence']):
        chosen_agent = "PDFRAGAgent"
    elif any(k in q_lower for k in ['arxiv', 'paper', 'research']):
        chosen_agent = "ArxivAgent"
    else:
        # 2. Intelligent Routing (LLM Decision)
        chosen_agent = controller.route_query(request.query)

    display_name = chosen_agent.replace("Agent", "")

    try:
        # 3. Execution Logic
        if "PDFRAG" in chosen_agent:
            result = pdf_agent.query_pdf(request.query)
        elif "WebSearch" in chosen_agent:
            result = web_agent.search(request.query)
        elif "Arxiv" in chosen_agent:
            result = arxiv_agent.fetch_papers(request.query)
        else:
            resp = client.models.generate_content(model=MODEL_ID, contents=request.query)
            result = resp.text
            display_name = "Ignis"

    except Exception as e:
        if "429" in str(e):
            result = "The AI is currently busy. Please wait 60 seconds."
        else:
            result = f"Execution Error: {str(e)}"

    return {"agent": display_name, "result": result}