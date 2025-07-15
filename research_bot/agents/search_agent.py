from agents import Agent, WebSearchTool
from agents.model_settings import ModelSettings
from .prompts.prompts import SEARCH_AGENT_INSTRUCTIONS

search_agent = Agent(
    name="Search agent",
    instructions=SEARCH_AGENT_INSTRUCTIONS,
    tools=[WebSearchTool()],
    # Removed model_settings=ModelSettings(tool_choice="required") as it's not compatible with WebSearchTool
)

