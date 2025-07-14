import asyncio
import sys
from typing import List

import streamlit as st

# path hack as before to import external agents first
import os
curr_dir = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(curr_dir, os.pardir))
# make sure root is in path for `import research_bot` later
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

if curr_dir in sys.path:
    sys.path.remove(curr_dir)
from agents import Runner  # noqa: F401 ensure external agents loaded
sys.path.insert(0, curr_dir)

from research_bot.conversation_manager import ConversationManager

st.set_page_config(page_title="Research Bot", layout="wide")

st.title("🧑‍🔬 Research Bot")

st.markdown("Ask me to research anything. I'll clarify if needed, then deliver a full report.")

# ---------------- Session state ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # type: List[dict]
if "conv_mgr" not in st.session_state:
    st.session_state.conv_mgr = ConversationManager()

conv_mgr: ConversationManager = st.session_state.conv_mgr
# ensure attribute exists even for older instances
if not hasattr(conv_mgr, "last_report"):
    conv_mgr.last_report = None

# ---------- Chat history with inline report expander ----------
for idx, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        # If this assistant message is the research summary, immediately show report expander
        if m["role"] == "assistant" and m["content"].startswith("### Research Complete") and conv_mgr.last_report:
            with st.expander("📄 Full Report (Markdown)"):
                st.markdown(conv_mgr.last_report.markdown_report, unsafe_allow_html=True)

# ---------------- Determine follow-up buttons ----------------
follow_up_lines: List[str] = []
if len(st.session_state.messages) >= 2:
    last = st.session_state.messages[-1]
    prev = st.session_state.messages[-2]
    if last["role"] == "assistant" and prev["role"] == "assistant" and "Research Complete" in prev["content"]:
        # last message likely contains newline-separated follow-ups
        follow_up_lines = [ln.strip("- ") for ln in last["content"].split("\n") if ln.strip()]
        if follow_up_lines:
            st.subheader("Follow-up questions:")
            for idx, ln in enumerate(follow_up_lines):
                if st.button(ln, key=f"fup_{idx}"):
                    st.session_state.user_input = ln  # inject into chat
                    st.rerun()

# ---------------- User input ----------------
user_input = st.chat_input("Type your message and press Enter")
if user_input is None:
    user_input = st.session_state.pop("user_input", None)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    async def backend_response(inp: str):
        return await conv_mgr.handle_user_message(inp)

# display spinner and then rerun after messages appended
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            assistant_msgs = asyncio.run(backend_response(user_input))
    for msg in assistant_msgs:
        st.session_state.messages.append(msg)

    st.rerun() 