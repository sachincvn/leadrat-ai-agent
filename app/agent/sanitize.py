"""Last line of defence between the model's answer and the user's screen.

Internal identifiers are useful to the agent - get_lead needs a lead's UUID,
get_user_profile needs a user's - so the tools hand them to the model. Nobody
reading a chat answer has any use for them, and a model asked for "my 10
leads" will happily print the id it was given. This strips them out of the
final text, and removes whatever label was introducing them, so the answer
never ends up with a dangling "Assigned To:" and nothing behind it.
"""

import re

_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

# "[User ID: <uuid>]", "(ID: <uuid>)" and friends - the whole bracketed aside.
_BRACKETED_ID = re.compile(rf"[\[(]\s*[\w ]*\bid\b\s*[:=]?\s*{_UUID}\s*[\])]", re.IGNORECASE)

# A whole line that is nothing but a label and an id: "Assigned To: <uuid>",
# "- Lead ID: <uuid>", "**ID**: <uuid>".
_LABELLED_ID_LINE = re.compile(
    rf"^[ \t]*[-*•]?[ \t]*\**[\w /]{{0,30}}\**[ \t]*[:=][ \t]*{_UUID}[ \t]*$",
    re.MULTILINE,
)

_BARE_UUID = re.compile(_UUID)

# A label left pointing at nothing once its id was removed.
_EMPTY_LABEL_LINE = re.compile(
    r"^[ \t]*[-*•]?[ \t]*\**[\w /]{1,30}\**[ \t]*[:=][ \t]*$", re.MULTILINE
)

# A line ending mid-phrase for the same reason, e.g. "Assigned to" once
# "[User ID: ...]" is gone.
_DANGLING_CONNECTIVE = re.compile(
    r"\b(assigned to|assigned|owned by|owner|handled by|id|ids)[ \t]*[:=]?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

_BLANK_RUN = re.compile(r"\n{3,}")


def _clean_line(line: str) -> str:
    cleaned = _BRACKETED_ID.sub("", line)
    cleaned = _LABELLED_ID_LINE.sub("", cleaned)
    cleaned = _BARE_UUID.sub("", cleaned)
    cleaned = _EMPTY_LABEL_LINE.sub("", cleaned)
    cleaned = _DANGLING_CONNECTIVE.sub("", cleaned)

    # Tidy what the removals left behind: whitespace pushed up against
    # punctuation, emptied brackets, orphaned separators, doubled spaces.
    cleaned = re.sub(r"[ \t]+([,.;:)\]])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s*\)|\[\s*\]", "", cleaned)
    # A trailing "|" is left alone - in a markdown table it closes the row.
    cleaned = re.sub(r"[ \t]*[,;][ \t]*$", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.rstrip()


def strip_internal_ids(text: str) -> str:
    """Remove UUIDs, and any label left pointing at nothing, from an answer.

    Done line by line so that a line emptied by the removal disappears
    completely - leaving the blank would put a hole in the middle of a bullet
    list - while a blank line the model wrote as a paragraph break survives.
    """
    if not text:
        return text

    kept: list[str] = []
    for line in text.split("\n"):
        was_blank = not line.strip()
        cleaned = _clean_line(line)
        if cleaned.strip() or was_blank:
            kept.append(cleaned)

    return _BLANK_RUN.sub("\n\n", "\n".join(kept)).strip()
