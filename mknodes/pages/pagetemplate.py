from __future__ import annotations

from typing import TYPE_CHECKING

from mknodes import mkdocsconfig
from mknodes.pages import templateblocks
from mknodes.utils import reprhelpers


if TYPE_CHECKING:
    import markdown


class PageTemplate:
    def __init__(
        self,
        filename: str | None = None,
        extends: str | None = "base",
        parent=None,
    ):
        self.filename = filename
        self.extends = extends
        self.parent = parent
        self.title_block = templateblocks.TitleBlock()
        self.content_block = templateblocks.ContentBlock(parent)
        self.tabs_block = templateblocks.TabsBlock(parent)
        self.outdated_block = templateblocks.OutdatedBlock(parent)
        self.announce_block = templateblocks.AnnouncementBarBlock(parent)
        self.footer_block = templateblocks.FooterBlock(parent)
        self.libs_block = templateblocks.LibsBlock()
        self.styles_block = templateblocks.StylesBlock()
        self.hero_block = templateblocks.HeroBlock()

    def __bool__(self):
        return any(self.blocks)

    def __hash__(self):
        return hash(self.build_html())

    @property
    def blocks(self) -> list[templateblocks.Block]:
        return [
            self.title_block,
            self.content_block,
            self.tabs_block,
            self.announce_block,
            self.footer_block,
            self.libs_block,
            self.styles_block,
            self.outdated_block,
            self.hero_block,
        ]

    def __repr__(self):
        return reprhelpers.get_repr(
            self,
            filename=self.filename,
            extends=self.extends,
            _filter_empty=True,
        )

    @property
    def announcement_bar(self):
        return self.announce_block.content

    @announcement_bar.setter
    def announcement_bar(self, value):
        self.announce_block.content = value

    @property
    def content(self):
        return self.content_block.content

    @content.setter
    def content(self, value):
        self.content_block.content = value

    def build_html(self, md: markdown.Markdown | None = None) -> str | None:
        md = md or mkdocsconfig.Config().get_markdown_instance()
        blocks = ['{% extends "' + self.extends + '.html" %}\n'] if self.extends else []
        blocks.extend(block.to_markdown(md) for block in self.blocks if block)
        return "\n".join(blocks) + "\n" if blocks else None


if __name__ == "__main__":
    import mknodes

    cfg = mkdocsconfig.Config()
    md = cfg.get_markdown_instance()
    template = PageTemplate(filename="main.html")
    template.announce_block.content = mknodes.MkAdmonition("test")
    html = template.build_html(md)
    print(html)
