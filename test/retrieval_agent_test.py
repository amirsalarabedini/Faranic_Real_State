import asyncio
from agents import Agent, FileSearchTool, Runner, WebSearchTool, function_tool
import os
# -----------------------------------------------------------------------------
# Retrieval agent (handles knowledge base / vector store search)
# -----------------------------------------------------------------------------
retrieval_agent = Agent(
    name="RetrievalAgent",
    instructions=(
        """
        You are a knowledge-retrieval assistant with access to an internal vector store.
        When the user asks a question, search the knowledge base and craft a structured
        answer using **exactly** the following four sections (use markdown headings):

        1. **executive_summary (The Core Answer):** Start with a direct, one-sentence answer.
           You may add 1-2 sentences of elaboration if absolutely necessary.
        2. **market_principles (The Why):** Explain the reasoning that led to your answer.
           Weave facts into a coherent argument instead of listing them randomly.
        3. **recommended_strategies (The Solutions):** Provide actionable next steps that
           logically follow from your analysis.
        4. **risks_and_mitigation (Considerations & Risks):** Briefly mention potential
           counter-arguments or challenges and how to mitigate them. Keep this concise.

        Stick to this format every time and do not add extra sections.Also connsider that answer only bsed on the retrieved knowledge.
        """
    ),
    tools=[
        FileSearchTool(
            max_num_results=5,
            vector_store_ids=["vs_687521bfdcf88191a98e649dbb56eb81"],
            include_search_results=True,
        )
    ],
    # You can specify a dedicated model if desired, otherwise it will inherit defaults
    model="o4-mini",
)


# -----------------------------------------------------------------------------
# Wrap the retrieval agent as a tool so that other agents can call it
# -----------------------------------------------------------------------------
@function_tool
async def retrieve_knowledge(question: str) -> str:  # type: ignore[valid-type]
    """Retrieve structured knowledge from the internal knowledge base."""
    result = await Runner.run(retrieval_agent, question)
    return str(result.final_output)


# -----------------------------------------------------------------------------
# Main assistant agent that uses web search and the retrieval tool
# -----------------------------------------------------------------------------
assistant_agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant. Use the retrieve_knowledge tool to get instructions from the internal knowledge base. then use the web search tool to get the latest information.",
    tools=[
        WebSearchTool(),
        retrieve_knowledge,  # <- our new retrieval tool replaces direct FileSearchTool usage
    ],
)


# -----------------------------------------------------------------------------
# Quick test harness
# -----------------------------------------------------------------------------
async def main() -> None:
    query = "الان منطقه ۱۳ تهران بهتر هستش برای سرمایه گذاری یا منطقه ۲۰؟"
    result = await Runner.run(assistant_agent, query)
    print("\n===== FINAL ANSWER =====\n")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main()) 