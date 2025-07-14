from __future__ import annotations

import asyncio
import time
import sys

from rich.console import Console

from agents import Runner, custom_span, gen_trace_id, trace, SQLiteSession

from .agents.clarifying_agent import ClarificationResult, clarifying_agent
from .agents.planner_agent import WebSearchItem, WebSearchPlan, planner_agent
from .agents.search_agent import search_agent
from .agents.writer_agent import ReportData, writer_agent
from .printer import Printer


class ResearchManager:
    def __init__(self):
        self.console = Console()
        self.printer = Printer(self.console)

    async def run(self, query: str) -> None:
        trace_id = gen_trace_id()
        with trace("Research trace", trace_id=trace_id):
            self.printer.update_item(
                "trace_id",
                f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}",
                is_done=True,
                hide_checkmark=True,
            )

            self.printer.update_item(
                "starting",
                "Starting research...",
                is_done=True,
                hide_checkmark=True,
            )
            
            # Clarify the query first
            clarified_query = await self._clarify_query(query)
            
            search_plan = await self._plan_searches(clarified_query)
            search_results = await self._perform_searches(search_plan)
            report = await self._write_report(clarified_query, search_results)

            final_report = f"Report summary\n\n{report.short_summary}"
            self.printer.update_item("final_report", final_report, is_done=True)

            self.printer.end()

        print("\n\n=====REPORT=====\n\n")
        print(f"Report: {report.markdown_report}")
        print("\n\n=====FOLLOW UP QUESTIONS=====\n\n")
        follow_up_questions = "\n".join(report.follow_up_questions)
        print(f"Follow up questions: {follow_up_questions}")

        # Return the report so that UI layers can display it
        return report

    async def _clarify_query(self, query: str) -> str:
        """Clarify the user's query by asking follow-up questions until it is clear."""
        self.printer.update_item(
            "clarifying", "Analyzing query for clarity...", is_done=False
        )

        # Use a dedicated session so that the clarifying agent remembers the conversation
        session = SQLiteSession(f"clarify_{gen_trace_id()}", ".db/clarify_history.db")

        current_query = query
        max_rounds = 3  # avoid infinite loops
        for round_idx in range(max_rounds):
            with custom_span("clarify_query_round"):
                result = await Runner.run(clarifying_agent, current_query, session=session)
                clar_res: ClarificationResult = result.final_output

                # If no clarification needed, we're done
                if not clar_res.needs_clarification:
                    clarified = clar_res.clarified_query or current_query
                    self.printer.update_item(
                        "clarifying",
                        f"Query clarified: {clar_res.reasoning}",
                        is_done=True,
                    )
                    return clarified

                # Ask user the clarification questions and gather answers
                answers: list[str] = []
                print("\n=== Clarification Required ===")
                for q in clar_res.clarification_questions:
                    if sys.stdin.isatty():
                        try:
                            user_answer = input(f"{q.question} \n> ")
                        except EOFError:
                            user_answer = ""
                    else:
                        # Non-interactive environment; skip waiting for user input
                        print("[Non-interactive] Skipping answer input.")
                        user_answer = ""
                    answers.append(f"Q: {q.question}\nA: {user_answer}")

                # Combine the original query with the answers to form a new prompt
                current_query = (
                    f"Original query: {query}\n\nUser clarifications:\n" + "\n".join(answers)
                )

        # Fallback if maximum rounds reached
        self.printer.update_item(
            "clarifying",
            "Proceeding with best clarified query after multiple attempts...",
            is_done=True,
        )
        return current_query

    async def _plan_searches(self, query: str) -> WebSearchPlan:
        """Plan the web searches to perform."""
        self.printer.update_item(
            "planning", "Planning web searches...", is_done=False
        )
        
        with custom_span("plan_searches"):
            result = await Runner.run(planner_agent, f"Query: {query}")
            
            self.printer.update_item(
                "planning",
                f"Planned {len(result.final_output.searches)} searches",
                is_done=True,
            )
            return result.final_output_as(WebSearchPlan)

    async def _perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
        """Perform the planned web searches."""
        with custom_span("Search the web"):
            self.printer.update_item("searching", "Searching...")
            num_completed = 0
            tasks = [asyncio.create_task(self._search(item)) for item in search_plan.searches]
            results = []
            for task in asyncio.as_completed(tasks):
                result = await task
                if result is not None:
                    results.append(result)
                num_completed += 1
                self.printer.update_item(
                    "searching", f"Searching... {num_completed}/{len(tasks)} completed"
                )
            self.printer.mark_item_done("searching")
            return results

    async def _search(self, item: WebSearchItem) -> str | None:
        """Perform a single web search."""
        input = f"Search term: {item.query}\nReason for searching: {item.reason}"
        try:
            result = await Runner.run(search_agent, input)
            return str(result.final_output)
        except Exception:
            return None

    async def _write_report(self, query: str, search_results: list[str]) -> ReportData:
        """Write the final report."""
        self.printer.update_item("writing", "Thinking about report...")
        input = f"Original query: {query}\nSummarized search results: {search_results}"
        result = Runner.run_streamed(writer_agent, input)
        update_messages = [
            "Thinking about report...",
            "Planning report structure...",
            "Writing outline...",
            "Creating sections...",
            "Cleaning up formatting...",
            "Finalizing report...",
            "Finishing report...",
        ]

        last_update = time.time()
        next_message = 0
        async for _ in result.stream_events():
            if time.time() - last_update > 5 and next_message < len(update_messages):
                self.printer.update_item("writing", update_messages[next_message])
                next_message += 1
                last_update = time.time()

        self.printer.mark_item_done("writing")
        return result.final_output_as(ReportData)
