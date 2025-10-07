# app/agents/controller.py

import google.generativeai as genai
from google.generativeai import GenerationConfig # For type hints and explicit config

class ControllerAgent:
    def __init__(self, llm_instance): # CORRECTED: Must take llm_instance
        self.llm = llm_instance
        print("Controller Agent initialized (Simple Routing).")

    def route_query(self, query: str) -> str:
        """
        Uses an LLM to decide which agent should handle the query.
        Returns the name of the agent as a single word (e.g., "WebSearchAgent").
        """
        prompt = f"""
        You are an intelligent routing agent. Your job is to determine the best tool for a user's query.
        You have the following tools available:
        - "PDFRAGAgent": Best for answering questions about a specific document.
        - "WebSearchAgent": Best for current events, breaking news, or general knowledge.
        - "ArxivAgent": **MUST BE USED if the query contains 'paper', 'research', 'arxiv', 'study', or 'abstracts'.**
        - "SynthesisOnly": Best for simple definitions or knowledge that requires no external look-up.

        Analyze the following user query and return only the single, exact name of the best agent to use. Do not add any other words or explanation.

        User Query: "{query}"

        Best Agent:
        """
        try:
            # Enforce fast, predictable routing with minimal tokens
            response = self.llm.generate_content(
                prompt,
                generation_config=genai.types.GenerateContentConfig(temperature=0.1, max_output_tokens=5)
            )
            agent_name = response.text.strip().replace("`", "").replace('"', '')
            return agent_name if agent_name in ["PDFRAGAgent", "WebSearchAgent", "ArxivAgent", "SynthesisOnly"] else "WebSearchAgent"
        except Exception as e:
            # Failsafe: if the LLM call fails, default to Web Search
            return "WebSearchAgent"