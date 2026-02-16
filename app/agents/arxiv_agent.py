import feedparser
import urllib.parse
import logging

logger = logging.getLogger("AgentSystemLogger")


class ArxivAgent:
    def __init__(self, client, model):
        self.client = client
        self.model = model
        self.base_url = "http://export.arxiv.org/api/query?"

    def fetch_papers(self, query: str, max_results: int = 3) -> str:
        """Fetches and summarizes recent academic research papers."""
        try:
            # Properly encode the query for the URL
            encoded_query = urllib.parse.quote(query)
            params = f"search_query=all:{encoded_query}&max_results={max_results}&sortBy=relevance"

            feed = feedparser.parse(self.base_url + params)

            if not feed.entries:
                return "No academic papers were found on ArXiv matching your research query."

            # Prepare paper abstracts for synthesis
            paper_summaries = []
            for entry in feed.entries:
                # Limit summary length to save tokens while keeping core info
                clean_summary = entry.summary.replace('\n', ' ')[:500]
                paper_summaries.append(f"TITLE: {entry.title}\nABSTRACT: {clean_summary}...")

            context = "\n\n---\n\n".join(paper_summaries)

            prompt = f"""
            SYSTEM: You are an academic research assistant. 
            Summarize the following ArXiv research papers related to the user's query.
            Highlight the core findings and methodology.

            --- RESEARCH DATA ---
            {context}

            --- RESEARCH QUERY ---
            {query}
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text.strip()

        except Exception as e:
            logger.error(f"Arxiv Error: {e}")
            return f"The Research portal (ArXiv) is temporarily unavailable: {str(e)}"