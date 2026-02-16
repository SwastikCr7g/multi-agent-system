import pypdf
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Optional


class PDFRAGAgent:
    def __init__(self, client, model):
        self.client = client
        self.model = model
        self.chunks = []
        self.index: Optional[faiss.IndexFlatL2] = None
        # This model is excellent for semantic similarity in RAG
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    def process_pdf(self, file_path: str) -> bool:
        """Improved PDF processing with structured chunking."""
        try:
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

            # Clean up excessive whitespace
            text = " ".join(text.split())

            # SLIDING WINDOW CHUNKING: Create overlapping chunks of ~500 characters
            # This ensures that if an answer is split between two paragraphs, it isn't lost.
            chunk_size = 600
            overlap = 150
            self.chunks = []

            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i:i + chunk_size]
                if len(chunk.strip()) > 50:  # Ignore tiny fragments
                    self.chunks.append(chunk.strip())

            if self.chunks:
                embs = self.embedder.encode(self.chunks)
                self.index = faiss.IndexFlatL2(embs.shape[1])
                self.index.add(np.array(embs, dtype=np.float32))
                return True
            return False
        except Exception as e:
            print(f"PDF Processing Error: {e}")
            return False

    def query_pdf(self, question: str):
        """Synthesizes high-accuracy answers using retrieved context."""
        if not self.index: return "No document has been uploaded or indexed yet."

        try:
            q_emb = self.embedder.encode([question])
            # Increased K to 6 to give the LLM a broader view of the document
            _, indices = self.index.search(np.array(q_emb, dtype=np.float32), 6)

            # De-duplicate and join retrieved context
            context_list = [self.chunks[idx] for idx in indices[0]]
            context = "\n---\n".join(context_list)

            prompt = f"""
            SYSTEM: You are a professional document analyzer. Use the provided text segments to answer the question.

            STRICT RULES:
            1. Answer ONLY using the provided context. 
            2. If the user asks for a summary (e.g., 'summarize in 5 sentences'), use the context to fulfill it exactly.
            3. If the information is missing, state 'The document does not contain this information.'
            4. Be concise and accurate.

            --- DOCUMENT CONTEXT ---
            {context}

            --- USER QUESTION ---
            {question}
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error during document analysis: {str(e)}"