"""Making a streamed answer safe to show while it is still arriving.

`strip_thinking` and `strip_internal_ids` both need whole lines: half a UUID
looks like ordinary text, and a `<think>` block can only be recognised once it
opens. So tokens are buffered here and released a line at a time - the user
sees the answer build up line by line, which is the part that makes the wait
feel short, without a raw id or a stray `<think>` ever reaching the screen.
"""

from collections.abc import Iterator

from app.agent.sanitize import strip_internal_ids

_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"


class SafeAnswerStream:
    """Feed it raw model chunks, take display-ready text out."""

    def __init__(self) -> None:
        self._buffer = ""
        self._in_thinking = False
        self._emitted_anything = False

    def feed(self, chunk: str) -> Iterator[str]:
        """Release every complete line the chunk finished off."""
        if not chunk:
            return
        self._buffer += chunk
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            text = self._release(line)
            if text is not None:
                yield text + "\n"

    def flush(self) -> Iterator[str]:
        """Release whatever is left once the model has stopped."""
        if self._buffer:
            text = self._release(self._buffer)
            self._buffer = ""
            if text is not None:
                yield text

    @property
    def produced_output(self) -> bool:
        """False when the whole answer was thinking, ids, or nothing at all."""
        return self._emitted_anything

    def _release(self, line: str) -> str | None:
        """One line, minus any reasoning and any id. None to drop it entirely.

        A line emptied by the scrubbing is dropped rather than sent as a blank,
        so a removed "Assigned To: <uuid>" leaves no hole - the same rule
        `strip_internal_ids` applies to a complete answer.
        """
        was_blank = not line.strip()
        visible = self._without_thinking(line)
        # Leading whitespace is markdown structure - it's what nests a list
        # item - and strip_internal_ids trims it, so put it back.
        indent = visible[: len(visible) - len(visible.lstrip())]
        cleaned = strip_internal_ids(visible)
        if cleaned:
            cleaned = indent + cleaned

        if not cleaned.strip():
            # Keep a blank line the model actually wrote (a paragraph break),
            # but only once something real has been shown before it.
            if was_blank and self._emitted_anything:
                return ""
            return None

        self._emitted_anything = True
        return cleaned

    def _without_thinking(self, line: str) -> str:
        """Drop the parts of this line inside a <think> block, tracking a block
        that opened on an earlier line and has not closed yet.
        """
        out = ""
        rest = line
        while rest:
            if self._in_thinking:
                _, marker, after = rest.partition(_THINK_CLOSE)
                if not marker:
                    return out  # still thinking; the rest of the line is hidden
                self._in_thinking = False
                rest = after
                continue

            before, marker, after = rest.partition(_THINK_OPEN)
            out += before
            if not marker:
                return out
            self._in_thinking = True
            rest = after
        return out
