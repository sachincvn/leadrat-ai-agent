"""Streamlit test UI. Run: streamlit run ui/app.py"""

import streamlit as st

from ui import api_client
from ui.config import BASE

st.set_page_config(page_title="MUSO AI", page_icon="💬")
st.title("MUSO AI — CRM Assistant")

st.session_state.setdefault("messages", [])

with st.sidebar:
    st.caption(f"Backend: {BASE}")

    jwt = st.text_area(
        "Leadrat JWT",
        value=st.session_state.get("jwt", ""),
        height=100,
        help="Needed when the backend runs against the live CRM (USE_MOCK_CRM=false).",
    ).strip()
    st.session_state["jwt"] = jwt

    try:
        st.json(api_client.health())
    except Exception as exc:
        st.error(f"Backend unreachable — {exc}")

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("tools_used"):
            st.caption("tools: " + ", ".join(msg["tools_used"]))

if prompt := st.chat_input("Ask about your leads..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"), st.spinner("Thinking..."):
        try:
            data = api_client.chat(prompt, jwt=jwt)
        except Exception as exc:
            data = {"answer": f"Request failed — {exc}", "tools_used": []}

        st.write(data["answer"])
        if data.get("tools_used"):
            st.caption("tools: " + ", ".join(data["tools_used"]))

    st.session_state.messages.append(
        {"role": "assistant", "content": data["answer"], "tools_used": data.get("tools_used", [])}
    )
