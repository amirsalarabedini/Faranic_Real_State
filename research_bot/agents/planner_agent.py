from pydantic import BaseModel

from agents import Agent
from .prompts.prompts import PLANNER_AGENT_PROMPT


class WebSearchItem(BaseModel):
    reason: str
    "Your reasoning for why this search is important to the query."

    query: str
    "The search term to use for the web search."


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem]
    """A list of web searches to perform to best answer the query."""


planner_agent = Agent(
    name="PlannerAgent",
    instructions=PLANNER_AGENT_PROMPT,
    model="gpt-4o",
    output_type=WebSearchPlan,
)
