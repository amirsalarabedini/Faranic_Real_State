"""
This module implements a multi-agent system with various joke styles
that can respond to user queries with different humor types.
"""
import requests
from bs4 import BeautifulSoup
from agents import Agent, function_tool, FileSearchTool
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from dotenv import load_dotenv
load_dotenv()



def create_agent(model=None):
    """
    Creates and returns the main real estate assistant agent.
    Args:
        model: The model to use for the agent (optional)
    Returns:
        An initialized Agent object
    """
    # --- Knowledge Base Agent ---
    kb_agent = Agent(
        name="Knowledge Base Agent",
        instructions="You are a real estate knowledge base assistant. Answer user questions using only the internal knowledge base. If the answer is not found, say so and suggest further research.",
        model=model,
        tools=[
            FileSearchTool(
                max_num_results=3,
                vector_store_ids=["vs_686ebb7f0a7481919851f455a6f08497"],
                include_search_results=True,
            )
        ],
    )

    # --- Research Agent ---
    research_agent = Agent(
        name="Research Agent",
        instructions="You are a real estate research assistant. When asked, perform deep research using real-time web data to answer user questions as accurately and up-to-date as possible.",
        model="o4-mini-deep-research",
    )

    # --- Decision (Triage) Agent ---
    decision_agent = Agent(
        name="Real Estate Decision Agent",
        instructions=prompt_with_handoff_instructions(
            """
            You are the main real estate assistant. When a user asks a question:
            - First, try to answer using the knowledge base agent.
            - If the knowledge base agent cannot answer or the user requests more up-to-date or detailed info, hand off to the research agent for real-time data.
            - If the user is satisfied, stop. If not, decide whether to continue searching the web or end the session.
            - Always choose the most efficient path to get the user the best real estate information.
            """
        ),
        handoffs=[kb_agent, research_agent],
        model=model,
    )

    return decision_agent