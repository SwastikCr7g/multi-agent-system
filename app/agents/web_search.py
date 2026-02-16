from duckduckgo_search import DDGS
import logging

logger = logging.getLogger("AgentSystemLogger")


class WebSearchAgent:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def search(self, query: str, max_results: int = 5) -> str:
        """
        Performs a real-time web search.
        Updated to use the News tool which has higher reliability against blocks.
        """
        try:
            results = []
            with DDGS(timeout=25) as ddgs:
                # Primary Attempt: News search (often bypasses the standard Bing/Duck block)
                ddgs_news_gen = ddgs.news(query, region='wt-wt', safesearch='moderate', timelimit='m')
                for r in ddgs_news_gen:
                    results.append({'title': r['title'], 'body': r['body']})
                    if len(results) >= max_results:
                        break

                # Secondary Attempt: If news is empty, try the standard web tool
                if not results:
                    ddgs_text_gen = ddgs.text(query, region='wt-wt', safesearch='moderate')
                    for r in ddgs_text_gen:
                        results.append({'title': r['title'], 'body': r['body']})
                        if len(results) >= max_results:
                            break

            if not results:
                # If both fail, the IP is likely flagged
                return "The WebSearch portal is currently under maintenance or rate-limited. Please try again later."

            # Constructing a rich context for the LLM
            context_list = [f"Source: {r['title']}\nSnippet: {r['body']}" for r in results]
            context = "\n---\n".join(context_list)

            prompt = f"""
            SYSTEM: You are a real-time information synthesizer. 
            Use the following search results to provide a concise, accurate answer to the user query.
            Always cite key facts if multiple sources agree.

            --- WEB SEARCH RESULTS ---
            {context}

            --- USER QUERY ---
            {query}
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text.strip()

        except Exception as e:
            logger.error(f"WebSearch Error: {e}")
            if "ratelimit" in str(e).lower():
                return "The WebSearch portal is currently rate-limited. Please try again in a moment."
            return f"The WebSearch portal encountered an issue: {str(e)}"