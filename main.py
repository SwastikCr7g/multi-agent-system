import os
import google.generativeai as genai
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, List
from pathlib import Path
import json # Used for error logging

# Local imports
from .schemas import AskRequest
from .agents.controller import ControllerAgent
from .agents.pdf_rag import PDFRAGAgent
from .agents.web_search import WebSearchAgent
from .agents.arxiv_agent import ArxivAgent

# --- PATH AND LOGGING SETUP ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

os.makedirs(LOG_DIR, exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = LOG_DIR / "agent_system.log"
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
file_handler.setFormatter(log_formatter)
logger = logging.getLogger("AgentSystemLogger")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

load_dotenv(PROJECT_ROOT / ".env")
app = FastAPI(title="Multi-Agent AI System")

# --- Agent Initialization ---
llm_model = None
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found.")

    genai.configure(api_key=api_key)
    llm_model = genai.GenerativeModel('gemini-flash-latest')
    logger.info("Central Gemini LLM model initialized successfully.")

except Exception as e:
    logger.critical(f"FATAL: Failed to initialize Gemini LLM model: {e}")

if llm_model:
    controller = ControllerAgent(llm_instance=llm_model)
    pdf_agent = PDFRAGAgent(llm_instance=llm_model)
    web_agent = WebSearchAgent(llm_instance=llm_model)
    arxiv_agent = ArxivAgent(llm_instance=llm_model)
    logger.info("All agents initialized with shared LLM instance.")
else:
    logger.critical("FATAL: Application cannot run without LLM model.")
    controller, pdf_agent, web_agent, arxiv_agent = None, None, None, None

# --- Frontend and API Endpoints ---
app.mount("/frontend", StaticFiles(directory=PROJECT_ROOT / "frontend"), name="frontend")


@app.get("/")
async def read_index():
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")


# --- FINAL ROUTING FIX: HARDCODED KEYWORD CHECK ---
def determine_fixed_agent(query: str) -> str | None:
    """Checks for definitive keywords that mandate a specific agent (overriding LLM)."""
    query_lower = query.lower()

    # **CRITICAL FIX:** Force ArxivAgent for research-related terms.
    arxiv_keywords = ['paper', 'research', 'arxiv', 'study', 'abstracts']
    if any(keyword in query_lower for keyword in arxiv_keywords):
        return "ArxivAgent"

    # Secondary check for PDF/RAG terms (if user could query PDF via /ask)
    pdf_keywords = ['document', 'uploaded file', 'this pdf', 'file content']
    if any(keyword in query_lower for keyword in pdf_keywords):
        return "PDFRAGAgent"

    return None


@app.post("/ask")
async def ask(request: AskRequest) -> Dict[str, str]:
    logger.info(f"Received new query: '{request.query}'")
    if not controller:
        raise HTTPException(status_code=503, detail="LLM service is not available.")

    # 1. PRE-ROUTING: Check hardcoded rules FIRST (Solves the primary routing issue)
    fixed_agent = determine_fixed_agent(request.query)

    if fixed_agent:
        chosen_agent = fixed_agent
        # Rationale confirms the rule was used (kept for logging/traceability)
        rationale_detail = f"RULE: Forced to {fixed_agent[:-5]} Agent (Keyword Match)"
    else:
        # 2. LLM ROUTING: Only if no hard rule applies
        llm_choice = controller.route_query(request.query)
        chosen_agent = llm_choice
        rationale_detail = f"LLM ROUTED: {llm_choice}"

    logger.info(f"Controller chose agent: '{chosen_agent}' (Rule or LLM).")

    result = "Error: Agent processing failed."

    # 3. Execution
    if "PDFRAGAgent" in chosen_agent:
        result = "This query seems to be about a document. Please use the 'Personal PDF Assistant' section."
        display_agent_name = "PDFRAGAgent" # Set clean name
    elif "WebSearchAgent" in chosen_agent:
        result = web_agent.search(request.query)
        display_agent_name = "WebSearchAgent" # Set clean name
    elif "ArxivAgent" in chosen_agent:
        result = arxiv_agent.fetch_papers(request.query)
        display_agent_name = "ArxivAgent" # Set clean name
    else:
        # Fallback for SynthesisOnly or unexpected choice
        chosen_agent = "SynthesisOnly"
        display_agent_name = "SynthesisOnly" # Set clean name
        try:
            response = controller.llm.generate_content(f"Answer the user query: {request.query}")
            result = response.text
        except Exception as e:
            result = f"Synthesis failed: {str(e)}"

    # 4. Final Response
    # The 'display_agent_name' is now guaranteed to be a simple, clean string
    logger.info(f"Agent '{chosen_agent}' produced the following result: {result[:100]}...")
    return {"agent": display_agent_name, "result": result}


# --- LOGS, UPLOAD, QUERY ENDPOINTS (rest of main.py remains the same) ---
@app.get("/logs", response_class=PlainTextResponse)
async def get_logs():
    try:
        with open(log_file, "r") as f:
            return f.read()
    except FileNotFoundError:
        return "Log file not found."
    except Exception as e:
        return f"An error occurred while reading the log file: {str(e)}"


@app.post("/pdf-upload")
async def upload_pdf(file: UploadFile = File(...)):
    # Security check is intentionally kept minimal here.
    if not pdf_agent: raise HTTPException(status_code=503, detail="PDF service is not available.")
    if not file.filename.endswith('.pdf'): raise HTTPException(status_code=400, detail="Invalid file type.")

    save_path = LOG_DIR / file.filename

    try:
        with open(save_path, "wb") as f:
            f.write(await file.read())

        if pdf_agent.process_pdf(str(save_path)):
            return {"filename": file.filename, "status": "PDF processed successfully."}
        else:
            raise HTTPException(status_code=500, detail="Failed to process PDF.")
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query-pdf")
async def query_pdf_endpoint(question: str = Form(...)):
    if not pdf_agent or pdf_agent.index is None:
        raise HTTPException(status_code=400, detail="No PDF has been processed yet. Please upload a document first.")

    answer = pdf_agent.query_pdf(question)
    return {"answer": answer}