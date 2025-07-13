import asyncio
from typing import List

from agents import Runner, SQLiteSession

from research_bot.agents.clarifying_agent import clarifying_agent, ClarificationResult


def build_prompt(original_query: str, answers: List[str]) -> str:
    """Combine the original query with user-provided answers so the clarifying agent has context."""
    if not answers:
        return original_query

    answer_blocks = "\n".join(f"Answer {i+1}: {ans}" for i, ans in enumerate(answers))
    return f"Original query: {original_query}\n{answer_blocks}"


async def clarify_query_interactively() -> str:
    """Interactively clarify a research query using the clarifying agent and user feedback."""
    original_query = input("Enter your research query: ")

    # Create a persistent session so the agent remembers the conversation
    session = SQLiteSession("clarify_session", "clarify_history.db")

    answers: List[str] = []
    current_input = original_query

    while True:
        # Run the clarifying agent with the combined prompt
        result = await Runner.run(
            clarifying_agent,
            build_prompt(original_query, answers),
            session=session,
        )
        clar_result = result.final_output  # type: ignore[assignment]

        # Safety check
        if not isinstance(clar_result, ClarificationResult):
            print("Error: Unexpected response type from clarifying agent. Aborting clarification.")
            return original_query

        if clar_result.needs_clarification and clar_result.clarification_questions:
            print("\nThe agent needs more information to clarify your query. Please answer the following questions:\n")
            for q in clar_result.clarification_questions:
                print(f"- {q.question}")
            print()
            # Collect user answers in the same order
            for q in clar_result.clarification_questions:
                ans = input(f"Your answer to '{q.question}': ")
                answers.append(ans)
            print()
            # Loop again with updated answers
            continue
        else:
            final_query = clar_result.clarified_query or original_query
            print("Query clarified!\n")
            print("Clarified Query:")
            print(final_query)
            print("\nReasoning:")
            print(clar_result.reasoning)
            return final_query


def main() -> None:
    asyncio.run(clarify_query_interactively())


if __name__ == "__main__":
    main() 