"""Report tools: the twelve CRM reports, one file per report.

Every one takes the same filter surface and returns rows plus totals; what
differs is only what the rows are grouped by. The shared request, scope and
tenant routing live in `_shared.py` and `endpoints/run_report.py`.
"""

from app.agent.tools.report.get_activity_report import get_activity_report
from app.agent.tools.report.get_call_report import get_call_report
from app.agent.tools.report.get_user_status_report import get_user_status_report
from app.agent.tools.report.get_user_substatus_report import get_user_substatus_report
from app.agent.tools.report.get_user_source_report import get_user_source_report
from app.agent.tools.report.get_user_subsource_report import get_user_subsource_report
from app.agent.tools.report.get_source_status_report import get_source_status_report
from app.agent.tools.report.get_subsource_status_report import get_subsource_status_report
from app.agent.tools.report.get_project_status_report import get_project_status_report
from app.agent.tools.report.get_country_status_report import get_country_status_report
from app.agent.tools.report.get_campaign_substatus_report import get_campaign_substatus_report
from app.agent.tools.report.get_channel_partner_substatus_report import get_channel_partner_substatus_report
from app.agent.tools.report.get_revenue_source_report import get_revenue_source_report
from app.agent.tools.report.get_revenue_subsource_report import get_revenue_subsource_report

REPORT_TOOLS = [
    get_activity_report,
    get_call_report,
    get_user_status_report,
    get_user_substatus_report,
    get_user_source_report,
    get_user_subsource_report,
    get_source_status_report,
    get_subsource_status_report,
    get_project_status_report,
    get_country_status_report,
    get_campaign_substatus_report,
    get_channel_partner_substatus_report,
    get_revenue_source_report,
    get_revenue_subsource_report,
]
