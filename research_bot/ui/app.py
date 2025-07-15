"""Streamlit Research Bot – resilient, Cloud‑safe version with continuing chat after follow‑ups
===========================================================================================

Changes in this revision
------------------------
* **Follow‑up continuity** – clicking a follow‑up now clears the previous report and allows a new
  agent run; `st.stop()` is only triggered when the app is *not* processing.
* **State resets** – `ask_user()` now resets `report_md` and `followups` so the next rerun shows
  the live conversation instead of the old report.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import List, Dict, Any

import streamlit as st

# -----------------------------------------------------------------------------
#  Import runner & conversation manager (same mechanics as original file)
# -----------------------------------------------------------------------------
CUR_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CUR_DIR, os.pardir, os.pardir))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)  # ensure external "agents" takes priority

from agents import Runner  # type: ignore – external lib

sys.path.insert(0, PROJECT_ROOT)  # local imports now OK
from research_bot.conversation_manager import ConversationManager

# ─────────────────────────────  Streamlit config  ─────────────────────────────
st.set_page_config(page_title="Research Bot", layout="wide")

CSS_PATH = os.path.join(CUR_DIR, "static", "style.css")
if os.path.exists(CSS_PATH):
    with open(CSS_PATH) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🧑‍🔬 Research Bot")
st.markdown("Ask me anything to research. I will clarify if needed, search the web, and deliver a full markdown report.")

# ───────────────────────────  Session state setup  ────────────────────────────
DEFAULTS: Dict[str, Any] = {
    "messages": [],                    # chat history
    "conv_mgr": ConversationManager(), # long‑lived agent
    "report_md": None,                # last markdown report (str)
    "followups": [],                  # list[str]
    "processing": False,              # flag while agent works
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

conv_mgr: ConversationManager = st.session_state.conv_mgr

# ──────────────────────────  Helper render functions  ─────────────────────────

def render_chat() -> None:
    """Display the full chat including the last assistant summary and report."""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Render stored report only when we're idle, not while processing a new prompt
    if st.session_state.report_md and not st.session_state.processing:
        st.header("Research Complete")
        with st.expander("📄 Full Report (Markdown)", expanded=True):
            st.markdown(st.session_state.report_md, unsafe_allow_html=True)

        if st.session_state.followups:
            st.subheader("💡 Follow‑up Questions:")
            for i, q in enumerate(st.session_state.followups):
                if st.button(q, key=f"fu_{i}"):
                    ask_user(q)  # clears report & starts new run
        # Prevent duplicate input box when idle
        st.stop()

# ─────────────────────────────  Async utilities  ──────────────────────────────
async def get_response_async(prompt: str) -> List[Dict[str, str]]:
    """Delegate to the ConversationManager (your custom async implementation)."""
    return await conv_mgr.handle_user_message(prompt)

# ─────────────────────────────  Core input logic  ─────────────────────────────

def ask_user(prompt: str) -> None:
    """Handle user prompt – runs agent, persists results, triggers rerun."""
    # reset previous outcome so it doesn't block the UI on next pass
    st.session_state.report_md = None
    st.session_state.followups = []

    # append user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.processing = True
    st.rerun()  # redraw now with spinner & disabled input


def run_agent_and_store(prompt: str) -> None:
    """Long‑running step that calls the async agent and stores results."""
    with st.spinner("Thinking…"):
        try:
            assistant_msgs = asyncio.run(get_response_async(prompt))
        except Exception as exc:  # noqa: BLE001
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Sorry, I encountered an error: {exc}",
            })
            st.session_state.processing = False
            return

    # Expect first assistant message to contain summary + report link etc.
    if assistant_msgs and "Research Complete" in assistant_msgs[0]["content"]:
        report_obj = getattr(conv_mgr, "last_report", None)
        if report_obj:
            st.session_state.report_md = report_obj.markdown_report  # type: ignore[attr-defined]

        # Extract follow‑ups from last assistant message (simple blank‑line split)
        followups_raw = assistant_msgs[-1]["content"].strip().split("\n\n")
        st.session_state.followups = [q.strip() for q in followups_raw if q.strip()]

    # Persist assistant messages (strings only) and finish
    st.session_state.messages.extend(assistant_msgs)
    st.session_state.processing = False
    st.rerun()

# ───────────────────────────────  UI pipeline  ────────────────────────────────
render_chat()  # may call st.stop() if report already shown and idle

# Show input or a disabled stub depending on processing flag
if st.session_state.processing:
    st.chat_input("Processing… Please wait", disabled=True)
else:
    user_text = st.chat_input("Type and press Enter")
    if user_text:
        ask_user(user_text)

# If we just added a prompt in the *previous* rerun, do the heavy work now
if st.session_state.processing and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"]
    run_agent_and_store(last_prompt)
