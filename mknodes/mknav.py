from __future__ import annotations

from collections.abc import Sequence
import logging
import os
import pathlib
import re
import types

from typing import TYPE_CHECKING

import mkdocs_gen_files

from typing_extensions import Self

from mknodes import mknav, mknode, mkpage, mktext
from mknodes.utils import helpers


if TYPE_CHECKING:
    from mknodes import mkdoc
    from mknodes.classnodes import mkclasspage

logger = logging.getLogger(__name__)


class MkNav(mknode.MkNode):
    """Nav section, representing a nestable menu.

    A nav has a section name (exception can be the root), an associated virtual file
    (in general a SUMMARY.md) and can contain other navs as well as pages.

    Arguments:
        section: Section name for the Nav
        filename: FileName for the resulting nav
    """

    def __init__(
        self,
        section: str | None = None,
        *,
        filename: str = "SUMMARY.md",
        **kwargs,
    ):
        super().__init__(**kwargs)
        # self.section = helpers.slugify(section) if section else None
        self.section = section
        self.filename = filename
        self.path = (
            pathlib.Path(section) / self.filename
            if section
            else pathlib.Path(self.filename)
        ).as_posix()
        self.nav: dict[tuple | str | None, mknav.MkNav | mkpage.MkPage] = {}
        # self._mapping = {}
        # self._editor = mkdocs_gen_files.editor.FilesEditor.current()
        # self._docs_dir = pathlib.Path(self._editor.config["docs_dir"])
        # self.files = self._editor.files

    def __repr__(self):
        return helpers.get_repr(
            self,
            section=self.section or "<root>",
            filename=self.filename,
        )

    def __setitem__(self, item: tuple | str, node: mkpage.MkPage | MkNav):
        if isinstance(item, str):
            item = tuple(item.split("."))
        self.nav[item] = node

    def __getitem__(self, index: tuple) -> mkpage.MkPage | MkNav:
        return self.nav[index]

    @property
    def navs(self):
        return [node for node in self.nav.values() if isinstance(node, MkNav)]

    @property
    def pages(self):
        return [node for node in self.nav.values() if isinstance(node, mkpage.MkPage)]

    @property
    def children(self):
        return list(self.nav.values())

    @children.setter
    def children(self, items):
        self.nav = dict(items)

    def add_nav(self, section: str) -> MkNav:
        """Create a Sub-Nav, register it to given Nav and return it.

        Arguments:
            section: Name of the new nav.
        """
        navi = mknav.MkNav(section=section, parent=self)
        self._register(navi)
        return navi

    def add_index_page(
        self,
        hide_toc: bool = False,
        hide_nav: bool = False,
    ) -> mkpage.MkPage:
        page = mkpage.MkPage(
            path="index.md", hide_toc=hide_toc, hide_nav=hide_nav, parent=self
        )
        self.nav[None] = page
        return page

    def virtual_files(self) -> dict[str, str]:
        return {str(self.path): self.to_markdown()}

    def to_markdown(self) -> str:
        nav = mkdocs_gen_files.Nav()
        for path, item in self.nav.items():
            # current approach: index pages have path = None, they dont become part
            # of the literate nav.
            # Not sure what`s best here, lot of combinations possible with
            # section-index etc.
            if path is None:
                continue
            match item:
                case mkpage.MkPage():
                    nav[path] = pathlib.Path(item.path).as_posix()
                case MkNav():
                    nav[path] = f"{item.section}/"
                case _:
                    raise TypeError(item)
        return "".join(nav.build_literate_nav())

    def add_page(
        self,
        title: str,
        *,
        hide_toc: bool = False,
        hide_nav: bool = False,
        hide_path: bool = False,
        filename: str | None = None,
    ) -> mkpage.MkPage:
        """Add a page to the Nav."""
        page = mkpage.MkPage(
            path=filename or f"{title}.md",
            parent=self,
            hide_toc=hide_toc,
            hide_nav=hide_nav,
            hide_path=hide_path,
        )
        self._register(page)
        return page

    def add_doc(
        self,
        module: types.ModuleType | Sequence[str] | str,
        *,
        filter_by___all__: bool = False,
        section_name: str | None = None,
        class_page: type[mkclasspage.MkClassPage] | None = None,
        flatten_nav: bool = False,
    ) -> mkdoc.MkDoc:
        """Add a module documentation to the Nav.

        Arguments:
            module: The module to create a documentation section for.
            filter_by___all__: Whether the documentation
            section_name: Override the name for the menu (default: module name)
            class_page: Override for the default ClassPage
                        (default: [MkClassPage](MkClassPage.md))
            flatten_nav: Whether classes should be put into top-level of the nav
        """
        from mknodes import mkdoc

        nav = mkdoc.MkDoc(
            module=module,
            filter_by___all__=filter_by___all__,
            parent=self,
            section_name=section_name,
            class_page=class_page,
            flatten_nav=flatten_nav,
        )
        self._register(nav)
        return nav

    def _register(self, node):
        match node:
            case MkNav():
                self.nav[(node.section,)] = node
            case mkpage.MkPage():
                self.nav[node.path.removesuffix(".md")] = node

    @classmethod
    def from_file(cls, path: str | os.PathLike, section: str | None):
        content = pathlib.Path(path).read_text()
        return cls.from_text(content, section)
        # max_indent = max(len(line) - len(line.lstrip()) for line in content.split("\n"))
        # content = [line.lstrip() for line in content.split("\n")]

    @classmethod
    def from_text(cls, text: str, section: str | None):
        nav = cls(section)
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if match := re.match(r"\* \[(.*)\]\((.*\.md)\)", line):
                title = match[1]
                file_path = pathlib.Path(match[2])
                text = file_path.read_text()
                node = mktext.MkText(text)
                nav[title] = mkpage.MkPage(items=[node], path=file_path.name)
            elif match := re.match(r"\* \[(.*)\]\((.*)\/\)", line):
                subnav = MkNav(match[1])
                title = match[1]
                nav[title] = subnav
            elif match := re.match(r"\* (.*)", line):
                subnav_lines = []
                for subline in lines[i + 1 :]:
                    if subline.startswith("    "):
                        subnav_lines.append(subline[4:])
                    else:
                        break
                subnav = MkNav.from_text("\n".join(subnav_lines), section=match[1])
                title = match[1]
                nav[title] = subnav
        return nav

    @classmethod
    def from_folder(cls, folder: str | os.PathLike, parent=None) -> Self:
        folder = pathlib.Path(folder)
        nav = cls(folder.name, parent=parent)
        for path in folder.iterdir():
            if path.is_dir():
                subnav = cls.from_folder(folder / path.parts[-1], parent=nav)
                nav._register(subnav)
            elif path.suffix == ".md":
                page = mkpage.MkPage(path)
                nav._register(page)
        return nav


if __name__ == "__main__":
    docs = MkNav()
    nav_file = pathlib.Path(__file__).parent / "SUMMARY.md"
    # print(pathlib.Path(nav_file).read_text())
    nav = MkNav.from_file(pathlib.Path(__file__).parent / "SUMMARY.md", None)
    lines = [f"{level * '    '} {node!r}" for level, node in nav.iter_nodes()]
    print("\n".join(lines))
    # print(nav_file.read_text())
    # subnav = docs.add_nav("subnav")
    # page = subnav.add_page("My first page!")
    # page.add_admonition("Warning This is still beta", typ="danger", title="Warning!")
    # page2 = subnav.add_page("And a second one")
    # subsubnav = subnav.add_nav("SubSubNav")
    # subsubnav = subsubnav.add_page("SubSubPage")
    # from pprint import pprint

    # pprint(docs.all_virtual_files())
