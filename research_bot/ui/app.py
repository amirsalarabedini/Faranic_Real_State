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
if "current_report" not in st.session_state:
    st.session_state.current_report = None
if "current_followups" not in st.session_state:
    st.session_state.current_followups = []
if "show_report_for_message" not in st.session_state:
    st.session_state.show_report_for_message = -1  # Index of message to show report for

conv_mgr: ConversationManager = st.session_state.conv_mgr

# Ensure last_report attribute exists
if not hasattr(conv_mgr, "last_report"):
    conv_mgr.last_report = None

# ----------------- Render Chat History -----------------
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Show expander with full report if this is the right message
        if (msg["role"] == "assistant" and 
            "Research Complete" in msg["content"] and 
            st.session_state.current_report is not None and 
            i == st.session_state.show_report_for_message):
            with st.expander("📄 Full Report (Markdown)"):
                st.markdown(st.session_state.current_report.markdown_report)

# ----------------- Follow-up Questions Section -----------------
# Show follow-up questions if we have them and research is complete
if (st.session_state.current_followups and 
    len(st.session_state.messages) > 0 and 
    st.session_state.messages[-1]["role"] == "assistant"):
    
    # Check if the last assistant message indicates research completion
    last_assistant_msg = None
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant":
            last_assistant_msg = msg
            break
    
    if last_assistant_msg and "Research Complete" in last_assistant_msg["content"]:
        st.markdown("---")
        st.subheader("💡 Follow-up Questions:")
        
        # Display follow-up questions as buttons
        for i, question in enumerate(st.session_state.current_followups):
            question = question.strip()
            if question:
                if st.button(question, key=f"followup_{i}"):
                    st.session_state.user_input = question
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
    
    # Clear previous follow-ups when new input is received
    st.session_state.current_followups = []
    st.session_state.current_report = None
    st.session_state.show_report_for_message = -1

    async def backend(msg: str):
        return await conv_mgr.handle_user_message(msg)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            # Run async code in a separate thread to avoid event loop conflicts
            assistant_msgs = run_async_in_thread(backend(user_input))

    # Process assistant messages
    for m in assistant_msgs:
        st.session_state.messages.append(m)
        # Render the assistant message immediately so the user sees it
        with st.chat_message(m["role"]):
            st.markdown(m["content"], unsafe_allow_html=True)
        
        # Check if this is a research completion message
        if m["role"] == "assistant" and "Research Complete" in m["content"]:
            # Store the report and set the message index to show it for
            if conv_mgr.last_report:
                st.session_state.current_report = conv_mgr.last_report
                st.session_state.show_report_for_message = len(st.session_state.messages) - 1
    
    # After processing all messages, check if we got follow-up questions
    # The follow-up questions should be in a separate message after the research complete message
    if len(assistant_msgs) >= 2:
        # Check if the last message contains follow-up questions
        last_msg = assistant_msgs[-1]
        if last_msg["role"] == "assistant" and last_msg["content"].strip():
            # Parse follow-up questions from the content
            content = last_msg["content"].strip()
            # Split by double newlines and filter out empty strings
            questions = [q.strip() for q in content.split("\n\n") if q.strip()]
            if questions:
                st.session_state.current_followups = questions
    
    # Force rerun to display follow-up questions
    st.rerun() 