import asyncio
import os
import sys
from typing import List

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
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(f"<div class='chat-message {msg['role']}'>" + msg["content"] + "</div>", unsafe_allow_html=True)
        # Show expander with full report right after the summary
        if msg["role"] == "assistant" and msg["content"].startswith("### Research Complete") and conv_mgr.last_report:
            with st.expander("📄 Full Report (Markdown)"):
                st.markdown(conv_mgr.last_report.markdown_report, unsafe_allow_html=True)

# ----------------- Follow-up Buttons -----------------
# More robust follow-up questions logic
def find_follow_up_questions():
    """Find follow-up questions in the message history"""
    if len(st.session_state.messages) < 2:
        return None
    
    # Look for the most recent research completion
    research_complete_idx = -1
    for i in range(len(st.session_state.messages) - 1, -1, -1):
        msg = st.session_state.messages[i]
        if msg["role"] == "assistant" and "Research Complete" in msg["content"]:
            research_complete_idx = i
            break
    
    if research_complete_idx == -1:
        return None
    
    # Look for follow-up questions in the next message after research complete
    if research_complete_idx + 1 < len(st.session_state.messages):
        follow_up_msg = st.session_state.messages[research_complete_idx + 1]
        if follow_up_msg["role"] == "assistant":
            # Extract follow-up questions from the content
            content = follow_up_msg["content"].strip()
            if content:
                # Split by double newlines and filter out empty lines
                questions = [q.strip() for q in content.split("\n\n") if q.strip()]
                return questions
    
    return None

# Display follow-up questions if available
follow_up_questions = find_follow_up_questions()
if follow_up_questions:
    st.subheader("Follow-up questions:")
    for i, question in enumerate(follow_up_questions):
        if st.button(question, key=f"followup_{i}"):
            st.session_state.user_input = question
            st.rerun()

# ----------------- User Input -----------------
user_input = st.chat_input("Type and press Enter")
if user_input is None:
    user_input = st.session_state.pop("user_input", None)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    async def backend(msg: str):
        return await conv_mgr.handle_user_message(msg)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            assistant_msgs = asyncio.run(backend(user_input))
    for m in assistant_msgs:
        st.session_state.messages.append(m)
    st.rerun() 