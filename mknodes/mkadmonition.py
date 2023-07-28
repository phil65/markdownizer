from __future__ import annotations

import logging
import textwrap

from typing import Literal

from mknodes import mktext
from mknodes.utils import helpers


logger = logging.getLogger(__name__)

AdmonitionTypeStr = Literal[
    "node",
    "abstract",
    "info",
    "tip",
    "success",
    "question",
    "warning",
    "failure",
    "danger",
    "bug",
    "example",
    "quote",
]


class MkAdmonition(mktext.MkText):
    """Admonition info box."""

    def __init__(
        self,
        text: str,
        typ: AdmonitionTypeStr = "info",
        *,
        title: str | None = None,
        collapsible: bool = False,
        expanded: bool = False,
        **kwargs,
    ):
        super().__init__(text=text, **kwargs)
        self.typ = typ
        self.title = title
        self.collapsible = collapsible
        self.expanded = expanded

    def __repr__(self):
        return helpers.get_repr(self, text=self.text, typ=self.typ, title=self.title)

    def _to_markdown(self) -> str:
        if not self.text:
            return ""
        block_start = "???" if self.collapsible else "!!!"
        if self.collapsible and self.expanded:
            block_start += "+"
        title = f' "{self.title}"' if self.title else ""
        text = textwrap.indent(str(self.text), "    ")
        return f"{block_start} {self.typ}{title}\n{text}\n"

    @staticmethod
    def examples():
        for typ in [
            "node",
            "abstract",
            "info",
            "tip",
            "success",
            "question",
            "warning",
            "failure",
            "danger",
            "bug",
            "example",
            "quote",
        ]:
            yield dict(typ=typ, text=f"This is type {typ}", title=typ)
        yield dict(typ="info", text="This is a collapsible menu", collapsible=True)


if __name__ == "__main__":
    admonition = MkAdmonition("")
    print(admonition)
