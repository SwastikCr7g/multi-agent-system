class ControllerAgent:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def route_query(self, query: str) -> str:
        """
        Intelligent routing that prioritizes PDFRAGAgent for document-specific tasks.
        Updated to ensure stable handoffs to real-time search and research agents.
        """
        prompt = f"""
        Analyze the user query and pick the best agent:
        - "PDFRAGAgent": Use if the user asks about 'this document', 'the pdf', 'summarize this', or specific facts likely in their uploaded file.
        - "WebSearchAgent": Use for general knowledge, current events, latest news, or real-time data.
        - "ArxivAgent": Use for academic papers, research, scientific studies, or 'arxiv'.
        - "SynthesisOnly": Use for simple greetings, direct math, or conversational chat without external data.

        Return ONLY the name of the agent.

        User Query: "{query}"
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            # Remove any markdown formatting or extra whitespace the model might include
            name = response.text.strip().replace("`", "").replace('"', '')

            # Validation check to ensure the output matches expected agent keys
            valid_agents = ["PDFRAGAgent", "WebSearchAgent", "ArxivAgent", "SynthesisOnly"]
            for agent in valid_agents:
                if agent.lower() in name.lower():
                    return agent

            # Default fallback to WebSearch if routing is ambiguous
            return "WebSearchAgent"
        except Exception:
            # Critical fallback to ensure the portal doesn't freeze
            return "WebSearchAgent"