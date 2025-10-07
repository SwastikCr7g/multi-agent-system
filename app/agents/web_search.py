# app/agents/web_search.py
from ddgs import DDGS
import google.generativeai as genai

class WebSearchAgent:
    def __init__(self, llm_instance):
        self.llm = llm_instance
        print("WebSearchAgent initialized (DDGS).")

    def search(self, query: str, max_results: int = 5) -> str:
        """Performs a web search using DDGS and synthesizes results."""
        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=max_results)]

            if not results:
                return "No real-time web results were found for your query."

            context_string = "\n---\n".join([
                f"Result {i + 1}:\nTitle: {r.get('title', 'N/A')}\nSnippet: {r.get('body', 'N/A')}"
                for i, r in enumerate(results)
            ])

            prompt = f"Based on these search snippets, answer: {query}\n\n{context_string}"
            response = self.llm.generate_content(prompt)
            return response.text

        except Exception as e:
            return f"The WebSearchAgent failed due to an environmental or network error: {str(e)}"