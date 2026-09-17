"""Streamlit test UI. Run: streamlit run ui/app.py"""

import base64
import json

import streamlit as st

from ui import api_client
from ui.config import BASE

st.set_page_config(page_title="MUSO AI", page_icon="💬")
st.title("MUSO AI - CRM Assistant")

st.session_state.setdefault("messages", [])


def tenant_from_jwt(token: str) -> str:
    """Read custom:tenant_id out of the token so the field pre-fills itself."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("custom:tenant_id", "")
    except Exception:
        return ""


with st.sidebar:
    st.caption(f"Backend: {BASE}")

    jwt = st.text_area(
        "Leadrat JWT",
        value=st.session_state.get("jwt", ""),
        height=100,
        help="Required - every CRM call is made as this user.",
    ).strip()
    st.session_state["jwt"] = jwt

    tenant = st.text_input(
        "Tenant",
        value=tenant_from_jwt(jwt),
        help="Sent as the 'tenant' header. Pre-filled from the token's custom:tenant_id claim.",
    ).strip()

    if jwt and st.button("Test CRM connection"):
        try:
            page = api_client.search_leads(jwt, tenant, limit=3)
            st.success(f"{page.get('total')} leads in this tenant")
            st.json(page)
        except Exception as exc:
            st.error(str(exc))

    try:
        st.json(api_client.health())
    except Exception as exc:
        st.error(f"Backend unreachable - {exc}")

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("tools_used"):
            st.caption("tools: " + ", ".join(msg["tools_used"]))

if prompt := st.chat_input("Ask about your leads..."):
    if not jwt:
        st.warning("Paste your Leadrat JWT in the sidebar first.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"), st.spinner("Thinking..."):
        try:
            data = api_client.chat(prompt, jwt=jwt, tenant=tenant)
        except Exception as exc:
            data = {"answer": f"Request failed - {exc}", "tools_used": []}

        st.write(data["answer"])
        if data.get("tools_used"):
            st.caption("tools: " + ", ".join(data["tools_used"]))

    st.session_state.messages.append(
        {"role": "assistant", "content": data["answer"], "tools_used": data.get("tools_used", [])}
    )
