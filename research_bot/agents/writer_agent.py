# Agent used to synthesize a final report from the individual summaries.
from pydantic import BaseModel

from agents import Agent
from .prompts.prompts import WRITER_AGENT_PROMPT


class ReportData(BaseModel):
    short_summary: str
    """A short 2-3 sentence summary of the findings."""

    markdown_report: str
    """The final report"""

    follow_up_questions: list[str]
    """Suggested topics to research further"""


writer_agent = Agent(
    name="WriterAgent",
    instructions=WRITER_AGENT_PROMPT,
    model="o4-mini",
    output_type=ReportData,
)
