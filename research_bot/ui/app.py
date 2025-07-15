import asyncio
import os
import sys
from typing import List, Dict, Any, Optional

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

# ----------------- Session State Initialization -----------------
def initialize_session_state():
    """Initialize all session state variables used in the app."""
    defaults = {
        "messages": [],
        "conv_mgr": ConversationManager(),
        "current_report": None,
        "current_followups": [],
        "processing": False,
    }
    
    # Set default values for any uninitialized state
    for key, default_value in defaults.items():
        st.session_state.setdefault(key, default_value)

initialize_session_state()

conv_mgr: ConversationManager = st.session_state.conv_mgr

# Ensure last_report attribute exists
if not hasattr(conv_mgr, "last_report"):
    conv_mgr.last_report = None

# ----------------- UI Helper Functions -----------------
def display_message(message: Dict[str, Any], index: int) -> None:
    """Display a single message in the chat interface."""
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show expander with full report if this is a research completion message
        if (message["role"] == "assistant" and 
            "Research Complete" in message["content"] and 
            st.session_state.current_report is not None):
            with st.expander("📄 Full Report (Markdown)"):
                st.markdown(st.session_state.current_report.markdown_report)

def display_follow_up_questions() -> None:
    """Display follow-up questions if available."""
    if not st.session_state.current_followups:
        return
        
    # Only show follow-up questions if the last message is from assistant and contains "Research Complete"
    if (st.session_state.messages and 
        st.session_state.messages[-1]["role"] == "assistant" and
        "Research Complete" in st.session_state.messages[-1]["content"]):
        
        st.markdown("---")
        st.subheader("💡 Follow-up Questions:")
        
        # Display follow-up questions as buttons
        for i, question in enumerate(st.session_state.current_followups):
            question = question.strip()
            if question:
                if st.button(question, key=f"followup_{i}"):
                    # Add the question as a user message and rerun
                    st.session_state.messages.append({"role": "user", "content": question})
                    st.session_state.current_followups = []
                    st.session_state.current_report = None
                    st.rerun()

def display_chat_history() -> None:
    """Display all messages in the chat history."""
    for i, message in enumerate(st.session_state.messages):
        display_message(message, i)

async def get_agent_response(prompt: str) -> List[Dict[str, Any]]:
    """Get response from the conversation manager."""
    return await conv_mgr.handle_user_message(prompt)

def process_assistant_messages(assistant_msgs: List[Dict[str, Any]]) -> None:
    """Process and display assistant messages, handling reports and follow-ups."""
    research_complete_found = False
    
    # Add all assistant messages to session state and display them
    for msg in assistant_msgs:
        st.session_state.messages.append(msg)
        
        # Display the message
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Check if this is a research completion message
            if msg["role"] == "assistant" and "Research Complete" in msg["content"]:
                research_complete_found = True
                # Store the report for display
                if conv_mgr.last_report:
                    st.session_state.current_report = conv_mgr.last_report
                    with st.expander("📄 Full Report (Markdown)"):
                        st.markdown(st.session_state.current_report.markdown_report)
    
    # If we found a research completion message, process follow-up questions
    if research_complete_found and len(assistant_msgs) >= 2:
        # The follow-up questions should be in the last message
        last_msg = assistant_msgs[-1]
        if last_msg["role"] == "assistant" and last_msg["content"].strip():
            # Extract follow-up questions from the content
            content = last_msg["content"].strip()
            # Split by double newlines and filter out empty strings
            questions = [q.strip() for q in content.split("\n\n") if q.strip()]
            if questions:
                st.session_state.current_followups = questions

def handle_user_input(user_input: str) -> None:
    """Handle user input and get agent response."""
    # Clear previous state
    st.session_state.current_followups = []
    st.session_state.current_report = None
    st.session_state.processing = True
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                # Run the async function properly
                assistant_msgs = asyncio.run(get_agent_response(user_input))
                st.session_state.processing = False
                
                # Process the assistant messages
                process_assistant_messages(assistant_msgs)
                
            except Exception as e:
                st.session_state.processing = False
                st.error(f"An error occurred: {str(e)}")
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Sorry, I encountered an error: {str(e)}"
                })

# ----------------- Main UI Flow -----------------

# Display chat history
display_chat_history()

# Display follow-up questions if available
display_follow_up_questions()

# Handle user input
if not st.session_state.processing:
    user_input = st.chat_input("Type and press Enter")
    if user_input:
        handle_user_input(user_input)
        st.rerun()
else:
    # Disable input while processing
    st.chat_input("Processing... Please wait", disabled=True) 