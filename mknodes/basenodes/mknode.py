from __future__ import annotations

import logging
import re
import textwrap

from typing import TYPE_CHECKING, Literal

from mknodes import paths
from mknodes.treelib import node


if TYPE_CHECKING:
    from mknodes import project

HEADER_REGEX = re.compile(r"^(#{1,6}) (.*)", flags=re.MULTILINE)


def shift_header_levels(text: str, levels: int) -> str:
    def mod_header(match: re.Match, levels: int) -> str:
        header_str = match[1]
        if levels > 0:
            header_str += levels * "#"
        else:
            header_str = header_str[:levels]
        return f"{header_str} {match[2]}"

    return re.sub(HEADER_REGEX, lambda x: mod_header(x, levels), text)


logger = logging.getLogger(__name__)


class MkNode(node.Node):
    """Base class for everything which can be expressed as Markup.

    The class inherits from Node. The idea is that starting from the
    root nav (aka Docs) down to nested Markup blocks, the whole project can be represented
    by one tree.

    MkNode is the base class for all nodes. We dont instanciate it directly.
    All subclasses carry an MkAnnotations node (except the MkAnnotations node itself)
    They can also pass an `indent` as well as a `shift_header_levels` keyword argument
    in order to modify the resulting markdown.
    """

    # METADATA (should be set by subclasses)

    ICON = "material/puzzle-outline"
    REQUIRED_EXTENSIONS: list[str] = []
    REQUIRED_PLUGINS: list[str] = []
    STATUS: Literal["new", "deprecated"] | None = None
    CSS = None
    children: list[MkNode]

    def __init__(
        self,
        header: str = "",
        indent: str = "",
        shift_header_levels: int = 0,
        project: project.Project | None = None,
        parent: MkNode | None = None,
    ):
        """Constructor.

        Arguments:
            header: Optional header for contained Markup
            indent: Indentation of given Markup (unused ATM)
            shift_header_levels: Regex-based header level shifting (adds/removes #-chars)
            project: Project this Nav is connected to.
            parent: Parent for building the tree
        """
        super().__init__(parent=parent)
        self.header = header
        self.indent = indent
        self._annotations = None
        self.shift_header_levels = shift_header_levels
        self._files: dict[str, str | bytes] = {}
        self._css_classes: set[str] = set()
        self._associated_project = project
        # ugly, but convenient.
        from mknodes.basenodes import mkannotations

        if not isinstance(self, mkannotations.MkAnnotations):
            self.annotations = mkannotations.MkAnnotations(parent=self)
        else:
            self.annotations = None

    def __str__(self):
        return self.to_markdown()

    def __hash__(self):
        return hash(self.to_markdown())

    def __eq__(self, other):
        if not type(other) == type(self):
            return False
        dct_1 = self.__dict__.copy()
        dct_1.pop("_parent")
        # dct_1.pop("_annotations")
        dct_2 = other.__dict__.copy()
        dct_2.pop("_parent")
        # dct_2.pop("_annotations")
        return dct_1 == dct_2

    def _to_markdown(self) -> str:
        return NotImplemented

    def to_markdown(self) -> str:
        """Outputs markdown for self and all children."""
        text = self._to_markdown()
        if self.shift_header_levels:
            text = shift_header_levels(text, self.shift_header_levels)
        if self.indent:
            text = textwrap.indent(text, self.indent)
        if self._css_classes:
            classes = " ".join(f".{kls_name}" for kls_name in self._css_classes)
            suffix = f"{{: {classes}}}"
            text += suffix
        if not self.header:
            return self.attach_annotations(text)
        header = self.header if self.header.startswith("#") else f"## {self.header}"
        text = f"{header}\n\n{text}"
        return self.attach_annotations(text)

    def attach_annotations(self, text: str) -> str:
        """Can be reimplemented if non-default annotations are needed."""
        return self.annotations.annotate_text(text) if self.annotations else text

    @property
    def resolved_parts(self) -> tuple[str, ...]:
        """Returns a tuple containing all section names."""
        from mknodes import mknav

        node = self
        parts = [self.section] if isinstance(self, mknav.MkNav) and self.section else []
        while node := node.parent:
            if isinstance(node, mknav.MkNav) and node.section:
                parts.append(node.section)
        return tuple(reversed(parts))

    def virtual_files(self):
        """Returns a dict containing the virtual files attached to this tree element.

        This can be overridden by nodes if they want files to be included in the build.
        """
        return self._files

    @property
    def resolved_virtual_files(self) -> dict[str, str | bytes]:
        """Return a dict containing all virtual files with resolved file paths."""
        from mknodes import mknav

        sections = [i.section for i in self.ancestors if isinstance(i, mknav.MkNav)]
        section = "/".join(i for i in reversed(sections) if i is not None)
        if section:
            section += "/"
        return {f"{section}{k}": v for k, v in self.virtual_files().items()}

    def add_file(self, filename: str, data: str | bytes):
        self._files[filename] = data

    def add_css_class(self, class_name: str):
        self._css_classes.add(class_name)

    def all_virtual_files(self, only_children: bool = False) -> dict[str, str | bytes]:
        """Return a dictionary containing all virtual files of itself and all children.

        Dict key contains the filename, dict value contains the file content.

        The resulting filepath is determined based on the tree hierarchy.
        """
        all_files: dict[str, str | bytes] = {}
        for des in self.descendants:
            all_files |= des.resolved_virtual_files
        if not only_children:
            all_files |= self.resolved_virtual_files
        return all_files

    def all_markdown_extensions(self) -> set[str]:
        extensions = {p for desc in self.descendants for p in desc.REQUIRED_EXTENSIONS}
        extensions.update(self.REQUIRED_EXTENSIONS)
        return extensions

    def all_plugins(self) -> set[str]:
        plugins = {p for desc in self.descendants for p in desc.REQUIRED_PLUGINS}
        plugins.update(self.REQUIRED_PLUGINS)
        return plugins

    def all_css(self) -> str:
        css_files: set[str] = {des.CSS for des in self.descendants if des.CSS}
        if self.CSS:
            css_files.add(self.CSS)
        css = ""
        for css_path in css_files:
            logger.debug("Appending %s to mknodes.css", css_path)
            file_path = paths.RESOURCES / css_path
            css += file_path.read_text()
        return css

    @staticmethod
    def create_example_page(page):
        import mknodes

        # We dont instanciate MkNode directly, so we take a subclass
        # to show some base class functionality

        node = mknodes.MkText("Intro\n# A header\nOutro")
        node.shift_header_levels = 2
        page += mknodes.MkReprRawRendered(node, header="### Shift header levels")

        node = mknodes.MkText("Every node can also append annotations (1)")
        node.annotations[1] = "Nice!"
        page += mknodes.MkReprRawRendered(node, header="### Append annotations")

    @property
    def associated_project(self):
        if proj := self._associated_project:
            return proj
        for ancestor in self.ancestors:
            if proj := ancestor._associated_project:
                return proj
        return None


if __name__ == "__main__":
    import mknodes

    section = mknodes.MkText("hello\n# Header\nfdsfds", shift_header_levels=2)
    print(section)
