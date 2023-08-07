from __future__ import annotations

import logging

from typing import Any

from mknodes.basenodes import mkcode, mknode, mktabcontainer
from mknodes.pages import mkpage
from mknodes.utils import helpers


logger = logging.getLogger(__name__)


def prep(node):
    node = node.__copy__()
    if isinstance(node, mkpage.MkPage):
        node.parent = None
        node.path = f"__{node.path}"
    return node


class MkReprRawRendered(mktabcontainer.MkTabbed):
    """MkCritic block."""

    ICON = "material/presentation"

    def __init__(self, node: mknode.MkNode, **kwargs: Any):
        """Constructor.

        Arguments:
            node: Node to show an example for
            kwargs: Keyword arguments passed to parent
        """
        repr_node = mkcode.MkCode(repr(node))
        if len(node.children) > 0:
            lines = [f"{level * '    '} {node!r}" for level, node in node.iter_nodes()]
            tree = mkcode.MkCode("\n".join(lines))
        else:
            tree = None
        markdown_node = mkcode.MkCode(prep(node), language="markdown")
        # TODO: hack: without doing this, we get issues because the page becomes
        # part of the tree. Perhaps add a setting for MkPages to be only-virtual?
        # Needs a general concept in regards to re-parenting. (should base nodes
        # be allowed to have pages as children?)
        self.node = node
        tabs: dict[str, str | mknode.MkNode] = dict(
            Repr=repr_node,
            Markdown=markdown_node,
            Rendered=prep(node),
        )
        if tree:
            tabs["Repr tree"] = tree
        super().__init__(tabs=tabs, select_tab=2, **kwargs)

    def __repr__(self):
        return helpers.get_repr(self, node=self.node)

    @staticmethod
    def create_example_page(page):
        import mknodes

        page.status = "new"  # for the small icon in the left menu
        example_node = mknodes.MkAdmonition("Some text")
        node = MkReprRawRendered(node=example_node)
        page += node
        page += MkReprRawRendered(node)


if __name__ == "__main__":
    import mknodes

    example_node = mknodes.MkAdmonition("Some text")
    node = MkReprRawRendered(node=example_node)
    print(node)
