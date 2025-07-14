import asyncio
from pathlib import Path
from typing import List, Dict, Any

from agents import Runner, SQLiteSession, gen_trace_id

from research_bot.agents.clarifying_agent import clarifying_agent, ClarificationResult
from research_bot.manager import ResearchManager


class ConversationManager:
    """Stateful manager that maintains a multi-turn research conversation."""

    def __init__(self, conversation_id: str | None = None, db_path: str | None = None):
        if conversation_id is None:
            conversation_id = f"conv_{gen_trace_id()}"
        if db_path is None:
            db_path = ".db/conversations.db"
        Path(db_path).parent.mkdir(exist_ok=True)
        self.session = SQLiteSession(conversation_id, db_path)

        # dialogue state
        self.phase: str = "waiting_query"  # waiting_query, clarify, research
        self.clar_res: ClarificationResult | None = None
        self.context_summaries: list[str] = []
        self.last_report = None
        self.initial_query: str = ""

    # ------------------------------------------------------------------
    async def handle_user_message(self, user_msg: str) -> List[Dict[str, Any]]:
        """Process a user message and return assistant messages to send back."""
        assistant_messages: list[dict] = []

        if self.phase == "waiting_query":
            # Run clarifier first round
            self.initial_query = user_msg
            clar_res = await self._run_clarifier(user_msg)
            if clar_res.needs_clarification:
                # Ask all questions in one message
                q_text = "\n".join([q.question for q in clar_res.clarification_questions])
                self.phase = "clarify"
                self.clar_res = clar_res
                assistant_messages.append({"role": "assistant", "content": q_text})
            else:
                self.phase = "research"
                clarified_query = clar_res.clarified_query or user_msg
                report = await self._run_research(clarified_query)
                assistant_messages.extend(self._report_to_messages(report))
                self.phase = "waiting_query"  # ready for next query
        elif self.phase == "clarify":
            # User provided answers to all questions in one message.
            combined_prompt = (
                f"Original query: {self.initial_query}\n\nUser clarifications:\n" + user_msg
            )
            clar_res = await self._run_clarifier(combined_prompt)
            self.phase = "research"
            clarified_query = clar_res.clarified_query or combined_prompt
            report = await self._run_research(clarified_query)
            assistant_messages.extend(self._report_to_messages(report))
            self.phase = "waiting_query"
        else:
            # If in research phase ignore user until finished
            assistant_messages.append({"role": "assistant", "content": "Please wait while I finish the research…"})

        return assistant_messages

    # ------------------------------------------------------------------
    async def _run_clarifier(self, prompt: str) -> ClarificationResult:
        res = await Runner.run(
            clarifying_agent,
            prompt,
            session=self.session,
        )
        return res.final_output

    async def _run_research(self, query: str):
        # Prepend previous summaries for context
        if self.context_summaries:
            prior = "\n---\n".join(self.context_summaries[-3:])
            combined = f"Previous context:\n{prior}\n\nCurrent query: {query}"
        else:
            combined = query
        class UIMgr(ResearchManager):
            async def _clarify_query(self, query: str):  # type: ignore[override]
                return query

        report = await UIMgr().run(combined)
        # Save summary and report for future context
        self.context_summaries.append(report.short_summary)
        self.last_report = report
        return report

    # helper not needed anymore

    # ------------------------------------------------------------------
    def _report_to_messages(self, report):
        return [
            {
                "role": "assistant",
                "content": f"### Research Complete\n\n**Summary:** {report.short_summary}",
            },
            {
                "role": "assistant",
                "content": "\n\n".join(report.follow_up_questions),
            },
        ] 