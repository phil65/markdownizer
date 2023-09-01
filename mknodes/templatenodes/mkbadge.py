from __future__ import annotations

import html
import logging

from typing import Any, Literal

import anybadge

from mknodes.basenodes import mkimage
from mknodes.utils import helpers, reprhelpers


logger = logging.getLogger(__name__)


StyleStr = Literal["default", "gitlab-scoped"]


class MkBadge(mkimage.MkImage):
    """Node for a locally-created badge (based on "anybadge").

    The node creates a badge svg, appends it to the virtual files, and
    shows it as an image.
    """

    ICON = "simple/shieldsdotio"

    def __init__(
        self,
        label: str,
        value: str,
        font_size: Literal[10, 11, 12] | None = None,
        font_name: str | None = None,
        num_padding_chars: int | None = None,
        badge_color: str | None = None,
        text_color: str | None = None,
        use_gitlab_style: bool = False,
        **kwargs: Any,
    ):
        """Constructor.

        Arguments:
            label: Left part of the badge
            value: Right part of the badge
            font_size: Size of font to use
            font_name: Name of font to use
            num_padding_chars: Number of chars to use for padding
            badge_color: Badge color
            text_color: Badge color
            use_gitlab_style: Use Gitlab-scope style
            kwargs: Keyword arguments passed to parent
        """
        super().__init__("", **kwargs)
        self.label = label
        self.value = value
        self.font_size = font_size
        self.font_name = font_name
        self.num_padding_chars = num_padding_chars
        self._badge_color = badge_color
        self._text_color = text_color
        self.use_gitlab_style = use_gitlab_style

    @property
    def badge_color(self) -> str | None:
        match self._badge_color:
            case None if self.associated_project:
                return self.associated_project.theme.get_primary_color()
            case str():
                return self._badge_color
        return None

    def _to_markdown(self):
        data = self.data.replace('<?xml version="1.0" encoding="UTF-8"?>', "")
        content = data.replace("\n", "")
        inner = f"<a href={self.url!r}>{content}</a>" if self.url else content
        return f"<body>{inner}</body>"

    @property
    def text_color(self) -> str | None:
        match self._text_color:
            case None if self.associated_project and self.use_gitlab_style:
                color = self.associated_project.theme.get_text_color()
                return f"{color},#fff"
            case None if self.associated_project:
                color = self.associated_project.theme.get_text_color()
                return f"#fff,{color}"
            case str():
                return self._text_color
        return None

    @property
    def data(self):
        badge = anybadge.Badge(
            label=html.escape(self.label),
            value=html.escape(self.value),
            font_size=self.font_size,
            font_name=self.font_name,
            num_padding_chars=self.num_padding_chars,
            default_color=self.badge_color,
            text_color=self.text_color,
            style="gitlab-scoped" if self.use_gitlab_style else "default",
        )
        return badge.badge_svg_text

    @data.setter
    def data(self, value):
        pass

    @property
    def path(self):
        unique = f"{self.label}_{self.value}_{hash(repr(self))}.svg"
        return helpers.slugify(unique)

    @path.setter
    def path(self, value):
        pass

    def __repr__(self):
        return reprhelpers.get_repr(
            self,
            label=self.label,
            value=self.value,
            font_size=self.font_size,
            font_name=self.font_name,
            badge_color=self.badge_color,
            text_color=self.text_color,
            num_padding_chars=self.num_padding_chars,
            use_gitlab_style=self.use_gitlab_style,
            _filter_empty=True,
            _filter_false=True,
        )

    @staticmethod
    def create_example_page(page):
        import mknodes

        node = MkBadge(label="Some", value="Badge")
        page += mknodes.MkReprRawRendered(node)
        node = MkBadge(label="Some", value="Badge", font_size=12)
        page += mknodes.MkReprRawRendered(node)
        node = MkBadge(label="Some", value="Badge", num_padding_chars=5)
        page += mknodes.MkReprRawRendered(node)
        node = MkBadge(label="Some", value="Badge", badge_color="teal")
        page += mknodes.MkReprRawRendered(node)
        node = MkBadge(label="Some", value="Badge", use_gitlab_style=True)
        page += mknodes.MkReprRawRendered(node)


if __name__ == "__main__":
    img = MkBadge("Left", "right")
    print(img.data)
