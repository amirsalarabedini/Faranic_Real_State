import asyncio
import os
import sys
from typing import List
import threading
import concurrent.futures

import streamlit as st

# --- Path fix to ensure external `agents` is imported before local research_bot.agents ---
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
# Temporarily remove project root to ensure external 'agents' resolves first
if project_root in sys.path:
    sys.path.remove(project_root)

from agents import Runner  # external library with Runner

# Re-add project root for local imports
sys.path.insert(0, project_root)

from research_bot.conversation_manager import ConversationManager

st.set_page_config(page_title="Research Bot", layout="wide")

# ---- Load static CSS ----
css_path = os.path.join(current_dir, "static", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🧑‍🔬 Research Bot")

st.markdown("Ask me anything to research. I will clarify if needed, search the web, and deliver a full markdown report.")

# ----------------- Session State -----------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # type: List[dict]
if "conv_mgr" not in st.session_state:
    st.session_state.conv_mgr = ConversationManager()
conv_mgr: ConversationManager = st.session_state.conv_mgr

# Ensure last_report attribute exists
if not hasattr(conv_mgr, "last_report"):
    conv_mgr.last_report = None

# ----------------- Render Chat History -----------------
st.write("DEBUG-messages:", st.session_state.messages)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # Display the raw markdown content without extra HTML wrapper to ensure compatibility across Streamlit versions
        st.markdown(msg["content"], unsafe_allow_html=True)
        # Show expander with full report right after the summary
        if msg["role"] == "assistant" and msg["content"].startswith("### Research Complete") and conv_mgr.last_report:
            with st.expander("📄 Full Report (Markdown)"):
                st.markdown(conv_mgr.last_report.markdown_report, unsafe_allow_html=True)

# ----------------- Follow-up Buttons -----------------
if len(st.session_state.messages) >= 2:
    last = st.session_state.messages[-1]
    prev = st.session_state.messages[-2]
    if last["role"] == "assistant" and prev["role"] == "assistant" and "Research Complete" in prev["content"]:
        followups = [ln.strip("- ") for ln in last["content"].split("\n") if ln.strip()]
        if followups:
            st.subheader("Follow-up questions:")
            for i, q in enumerate(followups):
                if st.button(q, key=f"fu_{i}"):
                    st.session_state.user_input = q
                    st.rerun()

# ----------------- User Input -----------------
user_input = st.chat_input("Type and press Enter")
if user_input is None:
    user_input = st.session_state.pop("user_input", None)

def run_async_in_thread(coro):
    """Run async coroutine in a separate thread to avoid event loop conflicts."""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        return future.result()

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    async def backend(msg: str):
        return await conv_mgr.handle_user_message(msg)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            # Run async code in a separate thread to avoid event loop conflicts
            assistant_msgs = run_async_in_thread(backend(user_input))

    for m in assistant_msgs:
        st.session_state.messages.append(m)
        # Render the assistant message immediately so the user sees it
        with st.chat_message(m["role"]):
            st.markdown(m["content"], unsafe_allow_html=True)
    # No explicit st.rerun(); Streamlit automatically reruns after chat_input event 