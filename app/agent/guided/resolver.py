"""Turns a model's action call into concrete UI steps the browser can run.

Two jobs, both security-relevant:

1. Validate the arguments. The local models this app runs against have no
   schema-enforcement mode, so an 8B model will happily invent an enum value or
   drop a required field. Everything is checked here, before a plan is built.
2. Expand the step template. The model never emits steps - it names an action,
   and the steps come from our own registry.
"""

import json
import re
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from app.agent.guided.registry import ACTIONS, Action

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
FILLABLE = ("to", "target", "value", "message", "key", "say")


class PlanItem:
    """One validated action, ready for the browser."""

    def __init__(self, call_id: str, action: Action, args: dict[str, str], steps: list[dict]):
        self.call_id = call_id
        self.action = action
        self.args = args
        self.steps = steps

    def as_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "action": self.action.name,
            "destructive": self.action.destructive,
            "args": self.args,
            "steps": self.steps,
        }


def _args_model(action: Action) -> type[BaseModel]:
    """Build the pydantic schema the model sees for one action."""
    fields: dict[str, Any] = {}
    for param in action.params:
        description = param.description
        if param.enum:
            description += f" One of: {', '.join(param.enum)}."
        if param.required:
            fields[param.name] = (str, Field(description=description))
        else:
            fields[param.name] = (str, Field(default="", description=description))
    return create_model(f"{action.name}_args", **fields)


def _unusable(*_args: Any, **_kwargs: Any) -> str:
    # Never reached: the runner intercepts UI actions by name and hands them to
    # the browser instead of invoking them. Present only so StructuredTool is valid.
    raise RuntimeError("UI actions are executed by the browser, not the server.")


def ui_tools() -> list[StructuredTool]:
    """The UI actions as tools, for binding to the model."""
    return [
        StructuredTool.from_function(
            func=_unusable,
            name=action.name,
            description=action.description,
            args_schema=_args_model(action),
        )
        for action in ACTIONS
    ]


def validate(action: Action, raw: dict[str, Any]) -> tuple[dict[str, str], str | None]:
    """Check the model's arguments against the action.

    Returns the cleaned arguments and an error message the model can act on.
    """
    known = {p.name: p for p in action.params}
    cleaned: dict[str, str] = {}
    problems: list[str] = []
    already_faulted: set[str] = set()

    for key, value in (raw or {}).items():
        param = known.get(key)
        if param is None:
            problems.append(f'"{key}" is not a parameter of {action.name}')
            continue
        text = "" if value is None else str(value).strip()
        if not text:
            continue
        if param.enum and text not in param.enum:
            problems.append(f'"{key}" must be one of: {", ".join(param.enum)} (got "{text}")')
            already_faulted.add(key)
            continue
        # A value the form itself would reject: caught here, while the model
        # can still correct it, rather than after the walkthrough has typed it.
        fault = param.check(text) if param.check else None
        if fault:
            problems.append(f'"{key}": {fault}')
            already_faulted.add(key)
            continue
        cleaned[key] = text

    for param in action.params:
        # A param that already failed its enum check does not also get reported
        # as missing - one clear problem per param, or the model over-corrects.
        if param.required and param.name not in cleaned and param.name not in already_faulted:
            problems.append(f'"{param.name}" is required')

    return cleaned, "; ".join(problems) or None


def resolve(call_id: str, action: Action, raw: dict[str, Any]) -> tuple[PlanItem | None, str | None]:
    """Validate arguments and expand the step template."""
    args, error = validate(action, raw)
    if error:
        return None, f'cannot run "{action.name}": {error}'

    steps: list[dict[str, Any]] = []
    for step in action.steps:
        missing = [k for k in PLACEHOLDER.findall(json.dumps(step)) if k not in args]
        if missing:
            if step.get("optional"):
                continue
            return None, (
                f'cannot run "{action.name}": missing value for {", ".join(missing)}'
            )

        resolved = {k: v for k, v in step.items() if k != "optional"}
        for key in FILLABLE:
            if isinstance(resolved.get(key), str):
                resolved[key] = PLACEHOLDER.sub(lambda m: args[m.group(1)], resolved[key])
        steps.append(resolved)

    return PlanItem(call_id, action, args, steps), None
