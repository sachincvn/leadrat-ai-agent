"""User tools - one file per CRM API.

Adding a tool:
    1. new file in this folder, named after the tool, holding one @tool function
    2. import it below and append it to USER_TOOLS

Only the two lines below are shared, so parallel work rarely conflicts.
"""

from langchain_core.tools import BaseTool

from app.agent.tools.user.get_my_profile import get_my_profile
from app.agent.tools.user.get_user_profile import get_user_profile
from app.agent.tools.user.list_users import list_users

USER_TOOLS: list[BaseTool] = [get_my_profile, list_users, get_user_profile]
