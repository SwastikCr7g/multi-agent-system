# app/agents/arxiv_agent.py
import feedparser
import urllib.parse
import google.generativeai as genai


class ArxivAgent:
    def __init__(self, llm_instance): # CORRECTED: Must take llm_instance
        self.llm = llm_instance
        self.base_url = "http://export.arxiv.org/api/query?"
        print("ArxivAgent initialized.")

    def fetch_papers(self, query: str, max_results: int = 3) -> str:
        """Fetches recent ArXiv papers and summarizes them with the LLM."""
        try:
            search_query = urllib.parse.quote_plus(query)
            query_params = f"search_query=all:{search_query}&sortBy=submittedDate&start=0&max_results={max_results}"
            feed = feedparser.parse(self.base_url + query_params)

            if not feed.entries:
                return "No recent academic papers found on ArXiv."

            context_string = "\n---\n".join([
                f"Paper: {e.title}\nAbstract: {e.summary[:300]}..."
                for e in feed.entries
            ])

            prompt = f"Summarize these recent academic findings based on the abstracts for the query: {query}\n\n{context_string}"
            response = self.llm.generate_content(prompt)
            return response.text

        except Exception as e:
            return f"ArxivAgent failed due to network error: {str(e)}"