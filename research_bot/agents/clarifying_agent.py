from pydantic import BaseModel

from agents import Agent
from .prompts.prompts import CLARIFYING_AGENT_PROMPT


class ClarificationQuestion(BaseModel):
    question: str
    """A specific follow-up question to clarify the user's intent."""
    
    reason: str
    """Explanation of why this question is important for effective research."""


class ClarificationResult(BaseModel):
    needs_clarification: bool
    """Whether the query needs clarification before proceeding with research."""
    
    clarified_query: str | None
    """If no clarification needed, an improved/clarified version of the original query."""
    
    clarification_questions: list[ClarificationQuestion]
    """List of questions to ask the user if clarification is needed."""
    
    reasoning: str
    """Explanation of the analysis and decision."""


clarifying_agent = Agent(
    name="ClarifyingAgent",
    instructions=CLARIFYING_AGENT_PROMPT,
    model="gpt-4o-mini",
    output_type=ClarificationResult,
) 