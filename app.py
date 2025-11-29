import streamlit as st
import asyncio
import sys
from utils import run_session
from agents import shopApp
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.memory import InMemoryMemoryService
from productstore import store
from baseClass import Product
from file_logger import log_trace


if sys.platform == "darwin":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

_loop = None

def get_event_loop():
    global _loop
    try:
        _loop = asyncio.get_event_loop()
        if _loop.is_closed():
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
    except RuntimeError:
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop

def get_agent_response(userPrompt: str) -> str:
    try:
        loop = get_event_loop()
        response = loop.run_until_complete(runner_creator(userPrompt))
        return response
    except Exception as e:
        import traceback
        st.error(f"Error: {str(e)}")
        st.error(traceback.format_exc())
        return "Error occurred while getting response."

async def runner_creator(userPrompt: str) -> str:
    session_service = DatabaseSessionService("sqlite+aiosqlite:///shopgenie_sessions.db")
    runner = Runner(
        app=shopApp,
        session_service=session_service,
        memory_service=InMemoryMemoryService()
    )
    return await run_session(runner, user_queries=userPrompt, session_name="user_id", session_service=session_service)

# def streamlit_starter():
#     # Configure page
#     st.set_page_config(page_title="ShopGenie", layout="centered", initial_sidebar_state="collapsed")
    
#     # Custom CSS for ChatGPT-like appearance
#     st.markdown("""
#     <style>
#         [data-testid="stChatMessageContainer"] {
#             background-color: #fff;
#         }
#         .stChatMessage {
#             padding: 1rem;
#         }
#     </style>
#     """, unsafe_allow_html=True)
    
#     st.title("ShopGenie")
    
#     # Initialize session state for chat history
#     if "messages" not in st.session_state:
#         st.session_state.messages = []
    
#     # Display chat history
#     for message in st.session_state.messages:
#         with st.chat_message(message["role"]):
#             st.markdown(message["content"])
    
#     # Chat input
#     if prompt := st.chat_input("Ask something..."):
#         # Add user message to history
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         with st.chat_message("user"):
#             st.markdown(prompt)
        
#         # Get agent response
#         with st.chat_message("assistant"):
#             with st.spinner("ShopGenie is thinking..."):
#                 response = get_agent_response(prompt)
#                 st.markdown(response)
        
#         # Add assistant message to history
#         st.session_state.messages.append({"role": "assistant", "content": response})
    
#     # Sidebar for additional options
#     with st.sidebar:
#         st.title("Options")
#         if st.button("View My Orders", key="view_orders"):
#             from sqlalchemy.orm import Session
#             from baseClass import Order
#             with Session(store.engine) as ses:
#                 rows = ses.query(Order).all()
#                 st.table([o.to_dict() for o in rows])
        
#         if st.button("Clear Chat History"):
#             st.session_state.messages = []
#             st.rerun()

# if __name__ == "__main__":
#     streamlit_starter()

import streamlit as st
import asyncio
import sys
import traceback

def streamlit_starter():
    st.set_page_config(page_title="ShopGenie", layout="centered", initial_sidebar_state="collapsed")
    try:
        st.markdown(
            """
            <style>
            :root{
                --card-width: 720px;
                --bg-color: #f7f9fc;
                --card-bg-color: #ffffff;
                --text-color: #2c3e50;
                --accent-start: #3498db;
                --accent-end: #2ecc71;
                --muted-color: #95a5a6;
            }
            html, body, [data-testid="stAppViewContainer"]{
                background-color: var(--bg-color);
                color: var(--text-color);
                font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
            }
            .center { display:flex; justify-content:center; margin-top:36px; margin-bottom:36px; }
            .chat-card{ width:var(--card-width); background: var(--card-bg-color); border-radius:16px; padding:20px; box-shadow: 0 10px 30px rgba(0,0,0,0.07); border: 1px solid #e8eaf0; }
            .header{ display:flex; align-items:center; gap:12px; margin-bottom:14px; }
            .logo { width:46px; height:46px; border-radius:10px; background: linear-gradient(135deg, var(--accent-start), var(--accent-end)); display:flex; align-items:center; justify-content:center; font-weight:700; color:white; font-size:18px; box-shadow: 0 4px 15px rgba(52, 152, 219, 0.3); }
            .title{ font-size:22px; font-weight:700; letter-spacing:0.2px; }
            .subtitle{ font-size:12px; color:var(--muted-color); margin-top:2px; }
            .chat-container{ height:520px; overflow:auto; padding:12px; border-radius:10px; background-color: #eaf6ff; border: 2px solid #d0e0f0; }
            .msg { display:flex; gap:10px; margin:8px 0; align-items:flex-end; }
            .msg .bubble { max-width:78%; padding:10px 12px; border-radius:12px; font-size:14px; line-height:1.45; white-space:pre-wrap; }
            .msg.user { justify-content:flex-end; }
            .msg.user .bubble { background: linear-gradient(90deg, var(--accent-start), var(--accent-end)); color:white; border-bottom-right-radius:6px; }
            .msg.assistant { justify-content:flex-start; }
            .msg.assistant .bubble { background-color: #e9ecef; color: var(--text-color); border-bottom-left-radius:6px; }
            .avatar { width:36px; height:36px; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; font-weight:700; color:white; flex:0 0 36px; }
            .bubble img { max-width: 100%; border-radius: 8px; margin-top: 10px; }
            .msg.assistant .bubble img {
                max-height: 250px;
                object-fit: contain;
            }
            .avatar.user { background: linear-gradient(90deg, var(--accent-start), var(--accent-end)); }
            .avatar.assistant { background-color: #bdc3c7; }            
            .avatar svg { width: 20px; height: 20px; }
            .muted { color:var(--muted-color); font-size:13px; }

            /* Style for the Streamlit form submit button */
            [data-testid="stFormSubmitButton"] > button {
                background: linear-gradient(90deg, var(--accent-start), var(--accent-end)) !important;
                color: white !important;
                border-radius: 10px !important;
                padding: 8px 14px !important;
                border: none !important;
                box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4) !important;
                font-weight: 600 !important;
            }
            /* Style for the text area */
            [data-testid="stTextArea"] > div > textarea {
                border: 1px solid #e8eaf0 !important;
                border-radius: 10px !important;
                padding: 8px 14px !important;
                border: none !important;
                box-shadow: 0 4px 15px rgba(52, 152, 219, 0.4) !important;
                font-weight: 600 !important;
            }
            .chat-container::-webkit-scrollbar { width:10px; }
            .chat-container::-webkit-scrollbar-thumb { background: #dce1e8; border-radius:8px; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="center"><div class="chat-card">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="header">
              <div class="logo"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 0-10 10c0 5.52 4.48 10 10 10s10-4.48 10-10A10 10 0 0 0 12 2z"/></svg></div>
              
              <div>
                <div class="title">ShopGenie</div>
                <div class="subtitle">AI assistant for your store — quick answers, order lookup, and help</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "messages" not in st.session_state:
            st.session_state.messages = [{"role":"assistant","content":"Hi — I'm ShopGenie. How can I help?"}]

        chat_placeholder = st.empty()
        def render_chat():
            html = ['<div class="chat-container">']
            for m in st.session_state.messages:
                role = m.get("role","assistant")
                content = m.get("content","")
                if role == "user":
                    # Escape user content to prevent HTML injection
                    content = content.replace("<","&lt;").replace(">","&gt;")
                    html.append(f'<div class="msg user"><div class="bubble">{content}</div><div class="avatar user"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div></div>')
                else:
                    # Assistant content is trusted (contains Markdown), so it's not escaped
                    html.append(f'<div class="msg assistant"><div class="avatar assistant"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg></div><div class="bubble">{content}</div></div>')
            html.append("</div>")
            chat_placeholder.markdown("".join(html), unsafe_allow_html=True)

        render_chat()

        with st.form("input_form", clear_on_submit=True):
            user_input = st.text_area("user_input", placeholder="Ask something — e.g. 'show my last order'", height=90, label_visibility="hidden")
            submit = st.form_submit_button("Send")
        if submit and user_input and user_input.strip():
            st.session_state.messages.append({"role": "user", "content": user_input.strip()})
            st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)

        with st.sidebar:
            st.title("Actions")
            view_orders = st.button("View My Orders")
            if st.button("Clear Chat History"):
                st.session_state.messages = [{"role":"assistant","content":"Hi — I'm ShopGenie. How can I help?"}]
                st.rerun()

        if view_orders:
            st.session_state.messages.append({"role":"user","content":"Show my orders"})
            st.rerun()
        
        # If the last message is from the user, get a response
        if st.session_state.messages[-1]["role"] == "user":
            with st.spinner("ShopGenie is thinking..."):
                prompt = st.session_state.messages[-1]["content"]
                resp = get_agent_response(prompt)
                log_trace(session_id="user_id", prompt=prompt, response=resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            st.rerun()

    except Exception as e:
        st.error("UI rendering error — check terminal for traceback")
        st.text(traceback.format_exc())

if __name__ == "__main__":
    streamlit_starter()