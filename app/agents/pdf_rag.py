# app/agents/pdf_rag.py
import pypdf
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import google.generativeai as genai
from typing import Optional


class PDFRAGAgent:
    def __init__(self, llm_instance, model_name='all-MiniLM-L6-v2'): # CORRECTED: Must take llm_instance
        self.llm = llm_instance # Store the LLM instance
        self.chunks = []
        self.index: Optional[faiss.IndexFlatL2] = None
        self.embedding_model = SentenceTransformer(model_name)
        self.generation_llm = genai.GenerativeModel('gemini-flash-latest') # Use a specific model for generation
        print("PDF RAG Agent initialized.")

    def process_pdf(self, file_path: str) -> bool:
        """Loads PDF, chunks, embeds, and creates a FAISS index."""
        # ... (rest of process_pdf is correct) ...
        try:
            reader = pypdf.PdfReader(file_path)
            full_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
            self.chunks = [p.strip() for p in full_text.split('\n\n') if len(p.strip()) > 30]
            if not self.chunks:
                self.index = None
                return False

            embeddings = self.embedding_model.encode(self.chunks, show_progress_bar=False)
            self.index = faiss.IndexFlatL2(embeddings.shape[1])
            self.index.add(np.array(embeddings, dtype=np.float32))
            return True
        except Exception as e:
            print(f"PDF processing failed: {e}")
            self.index = None
            return False

    def query_pdf(self, question: str, k: int = 4) -> str:
        """Retrieves passages and uses LLM for QA synthesis."""
        if self.index is None: return "Error: No PDF processed or RAG index is empty."
        try:
            question_embedding = self.embedding_model.encode([question])
            _, indices = self.index.search(np.array(question_embedding, dtype=np.float32), k)

            context = "\n\n---\n\n".join([self.chunks[i] for i in indices[0]])

            prompt = f"""
            SYSTEM: You are a helpful assistant. Based only on the retrieved text from the user's document, 
            answer the question concisely. If the information is not present, state that fact.

            --- Retrieved Document Text ---
            {context}
            --- End Text ---
            User's Question: {question}
            """
            # Use the generation LLM instance
            response = self.generation_llm.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"PDF query failed during retrieval or synthesis: {str(e)}"