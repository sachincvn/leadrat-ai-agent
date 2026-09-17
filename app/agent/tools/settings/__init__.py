"""Tenant settings tools, one file per API."""

from app.agent.tools.settings.get_global_settings import get_global_settings

SETTINGS_TOOLS = [get_global_settings]
