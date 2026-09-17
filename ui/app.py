"""Streamlit test UI. Run: streamlit run ui/app.py"""

import streamlit as st

from ui import api_client
from ui.config import BASE

st.set_page_config(page_title="MUSO AI", page_icon="💬")
st.title("MUSO AI — CRM Assistant")

st.session_state.setdefault("messages", [])

with st.sidebar:
    st.caption(f"Backend: {BASE}")
    lead_id = st.text_input("Selected lead", value="L001")
    jwt = st.text_area(
        "Leadrat JWT",
        value="",
        height=80,
        help="Only needed when the backend runs against the live CRM (USE_MOCK_CRM=false).",
    ).strip()

    try:
        st.json(api_client.health())
    except Exception as exc:
        st.error(f"Backend unreachable — {exc}")

    if lead_id:
        with st.expander("Lead record"):
            try:
                st.json(api_client.get_lead(lead_id, jwt))
            except Exception as exc:
                st.warning(str(exc))

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("tools_used"):
            st.caption("tools: " + ", ".join(msg["tools_used"]))

if prompt := st.chat_input("Ask about a lead..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"), st.spinner("Thinking..."):
        try:
            data = api_client.chat(prompt, lead_id, jwt)
        except Exception as exc:
            data = {"answer": f"Request failed — {exc}", "tools_used": []}

        st.write(data["answer"])
        if data.get("tools_used"):
            st.caption("tools: " + ", ".join(data["tools_used"]))

    st.session_state.messages.append(
        {"role": "assistant", "content": data["answer"], "tools_used": data.get("tools_used", [])}
    )
