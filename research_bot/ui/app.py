"""Streamlit Research Bot – v3  ▸  robust completion scan & smoother state flips
==========================================================================
Changes in this patch
--------------------
1. **Completion detection fixed** – we now scan *every* assistant message for
   the “Research Complete” marker instead of assuming it’s the first.
2. **Follow‑ups captured at the same spot** where the completion is detected so
   we never miss them.
3. **Processing flag flipped earlier** – we mark `processing = False` before
   saving `report_md` & `followups`, eliminating a transient UI state.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import List, Dict, Any

import streamlit as st

# ─────────────────────  Imports & path juggling  ─────────────────────
CUR_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CUR_DIR, os.pardir, os.pardir))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)

from agents import Runner  # external lib – takes priority

sys.path.insert(0, PROJECT_ROOT)
from research_bot.conversation_manager import ConversationManager

# ─────────────────────────  Streamlit config  ─────────────────────────
st.set_page_config(page_title="Research Bot", layout="wide")

CSS_PATH = os.path.join(CUR_DIR, "static", "style.css")
if os.path.exists(CSS_PATH):
    with open(CSS_PATH) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🧑‍🔬 Research Bot")
st.markdown("Ask me anything to research. I will clarify if needed, search the web, and deliver a full markdown report.")

# ───────────────────────────  State setup  ────────────────────────────
DEFAULTS: Dict[str, Any] = {
    "messages": [],
    "conv_mgr": ConversationManager(),
    "report_md": None,
    "followups": [],
    "processing": False,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

conv_mgr: ConversationManager = st.session_state.conv_mgr

# ───────────────────  Render helpers  ────────────────────

def render_chat() -> None:
    """Draw chat messages + optionally the stored report & follow‑ups."""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.report_md and not st.session_state.processing:
        st.header("Research Complete")
        with st.expander("📄 Full Report (Markdown)", expanded=True):
            st.markdown(st.session_state.report_md, unsafe_allow_html=True)

        if st.session_state.followups:
            st.subheader("💡 Follow‑up Questions:")
            for i, q in enumerate(st.session_state.followups):
                if st.button(q, key=f"fu_{i}"):
                    ask_user(q)  # fresh cycle
        st.stop()

# ───────────────────  Async wrapper  ────────────────────
async def get_response_async(prompt: str) -> List[Dict[str, str]]:
    return await conv_mgr.handle_user_message(prompt)

# ───────────────────  Input + agent glue  ────────────────────

def ask_user(prompt: str) -> None:
    """Queue a user prompt and trigger processing rerun."""
    st.session_state.report_md = None
    st.session_state.followups = []
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.processing = True
    st.rerun()


def run_agent_and_store(prompt: str) -> None:
    """Runs the agent, stores its output, and reruns UI."""
    with st.spinner("Thinking…"):
        try:
            assistant_msgs = asyncio.run(get_response_async(prompt))
        except Exception as exc:  # noqa: BLE001
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Sorry, I encountered an error: {exc}",
            })
            st.session_state.processing = False
            st.rerun()
            return

    # ── Begin post‑processing ─────────────────────────────────────────
    st.session_state.processing = False  # flip early so render_chat is safe

    # Find the first assistant message that signals completion
    report_found = False
    for msg in assistant_msgs:
        if msg["role"] == "assistant" and "Research Complete" in msg["content"]:
            report_found = True
            report_obj = getattr(conv_mgr, "last_report", None)
            if report_obj:
                st.session_state.report_md = report_obj.markdown_report  # type: ignore[attr-defined]

            followups_raw = msg["content"].strip().split("\n\n")
            st.session_state.followups = [q.strip() for q in followups_raw if q.strip()]
            break  # stop after first completion marker

    # Fallback – if we never saw the marker but the conv_mgr has a report, use it
    if not report_found:
        report_obj = getattr(conv_mgr, "last_report", None)
        if report_obj and not st.session_state.report_md:
            st.session_state.report_md = report_obj.markdown_report  # type: ignore[attr-defined]

    # Persist assistant messages and rerun
    st.session_state.messages.extend(assistant_msgs)
    st.rerun()

# ──────────────────────  UI pipeline  ──────────────────────
render_chat()

if st.session_state.processing:
    st.chat_input("Processing… Please wait", disabled=True)
else:
    txt = st.chat_input("Type and press Enter")
    if txt:
        ask_user(txt)

if st.session_state.processing and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    run_agent_and_store(st.session_state.messages[-1]["content"])
