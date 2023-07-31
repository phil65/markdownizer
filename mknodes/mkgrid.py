from __future__ import annotations

import logging

from mknodes import mkcontainer, mknode


logger = logging.getLogger(__name__)


class MkGridCard(mkcontainer.MkContainer):
    """Node representing a single tab."""

    def __init__(
        self,
        content: list | str | mknode.MkNode | None = None,
        **kwargs,
    ):
        super().__init__(content=content, **kwargs)

    def _to_markdown(self) -> str:
        item_str = "\n".join(i.to_markdown() for i in self.items)
        lines = item_str.split("\n")
        result = [f"-   {lines[0]}"]
        result.extend(f"    {i}" for i in lines[1:])
        return "\n".join(result) + "\n"


class MkGrid(mkcontainer.MkContainer):
    """Node for showing a formatted list."""

    def __init__(
        self,
        cards: list[str | mknode.MkNode] | None = None,
        *,
        header: str = "",
        **kwargs,
    ):
        match cards:
            case None:
                items = []
            case list():
                items = [
                    (card if isinstance(card, MkGridCard) else MkGridCard(card))
                    for card in cards
                ]
        for item in items:
            item.parent_item = self
        super().__init__(content=items, header=header, **kwargs)

    def _to_markdown(self) -> str:
        begin = '<div class="grid cards" markdown>'
        end = "</div>"
        content = "".join(str(i) for i in self.items) if self.items else ""
        return f"{begin}\n\n{content}\n{end}"

    @staticmethod
    def create_example_page(page):
        import mknodes

        # only works for Mkdocs-material sponsors.
        page.metadata["status"] = "new"
        item_1 = mknodes.MkList(items=["Item 1", "Item 2", "Item 3"])
        item_2 = mknodes.MkKeys(keys=["Ctrl+A"])
        grid = MkGrid(cards=[item_1, item_2])
        page += grid
        page += mknodes.MkCode(str(grid), language="markdown", header="Markdown")


if __name__ == "__main__":
    import mknodes

    keys = mknodes.MkKeys(keys="Ctrl+A")
    grid = MkGrid(cards=[keys, keys])
    print(grid)
