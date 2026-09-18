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

    st.divider()
    st.caption("Single-lead chat (stateless - no conversation id)")
    test_lead_id = st.text_input("Lead id", value="L001")
    test_lead_message = st.text_input(
        "Question (optional - leave blank for an automatic summary)", value=""
    )
    if st.button("Test lead chat"):
        if not jwt:
            st.warning("Paste your Leadrat JWT above first.")
        else:
            try:
                result = api_client.lead_chat(
                    test_lead_id, test_lead_message or None, jwt, tenant
                )
                st.write(result["Message"])
                for point in result.get("KeyHighlights", []):
                    st.markdown(f"- {point}")
            except Exception as exc:
                st.error(str(exc))

    if st.button("Clear chat"):
        # The backend remembers this conversation server-side (keyed off the
        # caller's JWT) - clear it there too, or the next message would still
        # pick up where the "forgotten" chat left off.
        if jwt:
            try:
                api_client.clear_chat_history(jwt, tenant)
            except Exception as exc:
                st.error(f"Could not clear server-side memory - {exc}")
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

    with st.chat_message("assistant"):
        status = st.empty()
        body = st.empty()
        status.caption("Working...")

        answer = ""
        tools_used: list[str] = []
        try:
            for event in api_client.chat_stream(prompt, jwt=jwt, tenant=tenant):
                kind = event.get("type")
                if kind == "status":
                    # Name the CRM call being made, so the wait is explained
                    # rather than just a spinner.
                    status.caption(f"Looking up {event['tool'].replace('_', ' ')}...")
                elif kind == "text":
                    answer += event["text"]
                    body.markdown(answer)
                elif kind == "done":
                    tools_used = event.get("tools_used", [])
                elif kind == "error":
                    answer = event["message"]
                    body.markdown(answer)
        except Exception as exc:
            answer = f"Request failed - {exc}"
            body.markdown(answer)

        status.empty()
        if tools_used:
            st.caption("tools: " + ", ".join(tools_used))

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "tools_used": tools_used}
    )
