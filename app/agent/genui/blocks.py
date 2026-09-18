"""The block contract: what the client is allowed to render.

A block is never authored by the model. The model chooses a tool; the tool
returns CRM data; a renderer in this package turns that data into one of the
fixed blocks below. So the UI can only ever show shapes that exist here, with
values that came from the CRM - a wrong prop or an invented component is not
reachable.

Adding a block:
    1. a name in BlockName, and the props it carries documented here
    2. a renderer in renderers.py that produces it from a tool's output
    3. the matching component in the web client's block registry
"""

from typing import Any, Literal

from pydantic import BaseModel

BlockName = Literal[
    "record_list",
    "lead_detail",
    "timeline",
    "stat_tiles",
    "data_table",
    "action_chips",
]

# Every CRM record the client can open. `kind` is what tells it which screen a
# row belongs to, so one list block serves leads, projects, properties and
# listings instead of four components that differ only in their route.
RecordKind = Literal["lead", "project", "property", "listing"]


class Block(BaseModel):
    """One renderable block, streamed alongside the answer text.

    props is deliberately loose here and precise in each renderer: the client
    ignores a block whose name it does not know, so a server that is ahead of
    a deployed client degrades to text rather than breaking.

    record_list  {"title": str, "kind": RecordKind, "total": int|None,
                  "records": [{"id", "title", "subtitle", "badge",
                               "details": [{"label", "value"}]}]}
    lead_detail  {"id", "name", "status", "phone", "email",
                  "fields": [{"label", "value"}]}
    timeline     {"title": str, "total": int|None,
                  "entries": [{"title", "detail", "by", "at"}]}
    stat_tiles   {"title": str, "tiles": [{"label": str, "value": int}]}
    data_table   {"title": str, "total": int|None,
                  "columns": [{"key": str, "label": str, "numeric": bool}],
                  "rows": [{<column key>: str|int|float|None}]}
    action_chips {"prompts": [str]}
    """

    name: BlockName
    props: dict[str, Any]
