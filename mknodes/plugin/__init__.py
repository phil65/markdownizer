"""The Mkdocs Plugin."""

from __future__ import annotations

# Partly based on mkdocs-gen-files
import collections
import importlib.util
import logging
import os
import pathlib
import sys
import tempfile
import types

from typing import TYPE_CHECKING
import urllib.parse

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.utils import write_file

from mknodes import project
from mknodes.plugin import linkreplacer, fileseditor

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page
    from mkdocs.structure.nav import Navigation


try:
    from mkdocs.exceptions import PluginError
except ImportError:
    PluginError = SystemExit  # type: ignore


try:
    from mkdocs.plugins import event_priority
except ImportError:

    def event_priority(priority):
        return lambda f: f  # No-op fallback


try:
    from mkdocs.plugins import get_plugin_logger

    logger = get_plugin_logger(__name__)
except ImportError:
    # TODO: remove once support for MkDocs <1.5 is dropped
    logger = logging.getLogger(f"mkdocs.plugins.{__name__}")  # type: ignore[assignment]


# For Regex, match groups are:
#       0: Whole markdown link e.g. [Alt-text](url)
#       1: Alt text
#       2: Full URL e.g. url + hash anchor
#       3: Filename e.g. filename.md
#       4: File extension e.g. .md, .png, etc.
#       5. hash anchor e.g. #my-sub-heading-link
AUTOLINK_RE = r"\[([^\]]+)\]\((([^)/]+\.(md|png|jpg))(#.*)*)\)"


def import_file(path: str | os.PathLike) -> types.ModuleType:
    """Import a module based on a file path.

    Arguments:
        path: Path which should get imported
    """
    module_name = pathlib.Path(path).stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class MkNodesPlugin(BasePlugin):
    config_scheme = (("script", config_options.Type(str)),)
    _edit_paths: dict
    css_filename = "mknodes.css"

    def on_files(self, files: Files, config: MkDocsConfig) -> Files:
        """On_files hook.

        During this phase all Markdown files as well as an aggregated css file
        are written.
        """
        self._dir = tempfile.TemporaryDirectory(prefix="mknodes_")
        self._project = project.Project(config=config, files=files)

        with fileseditor.FilesEditor(files, config, self._dir.name) as ed:
            file_name = self.config["script"]
            module = import_file(file_name)
            try:
                module.build(self._project)
            except SystemExit as e:
                if e.code:
                    msg = f"Script {file_name!r} caused {e!r}"
                    raise PluginError(msg) from e
            root = self._project._root
            if not root:
                msg = "No root for project created."
                raise RuntimeError(msg)
            for k, v in root.all_virtual_files(only_children=False).items():
                logger.info("Writing file to %s", k)
                mode = "w" if isinstance(v, str) else "wb"
                with ed.open(k, mode) as file:
                    file.write(v)
            css = root.all_css()
            if css:
                logger.info("Creating %s...", self.css_filename)
                config.extra_css.append(self.css_filename)
                path = pathlib.Path(config["site_dir"]) / self.css_filename
                write_file(css.encode(), str(path))
        self._edit_paths = dict(ed.edit_paths)
        return ed.files

    def on_nav(
        self,
        nav: Navigation,
        files: Files,
        config: MkDocsConfig,
    ) -> Navigation | None:
        self._file_mapping = collections.defaultdict(list)
        for file_ in files:
            filename = os.path.basename(file_.abs_src_path)  # noqa: PTH119
            self._file_mapping[filename].append(file_.url)
        return nav

    def on_page_markdown(
        self,
        markdown: str,
        *,
        page: Page,
        config: MkDocsConfig,
        files: Files,
    ) -> str | None:
        """During this phase [title](some_page.md) and °metadata stuff gets replaced."""
        #     print(file_.url, file_.dest_uri)
        docs_dir = config["docs_dir"]
        page_url = page.file.src_uri
        for k, v in self._project.info.metadata.items():
            if f"°metadata.{k}" in markdown or f"°metadata.{k.lower()}" in markdown:
                markdown = markdown.replace(f"°metadata.{k}", v)
                markdown = markdown.replace(f"°metadata.{k.lower()}", v)
                continue
        link_replacer = linkreplacer.LinkReplacer(docs_dir, page_url, self._file_mapping)
        return link_replacer.replace(markdown)

    def on_page_content(self, html, page: Page, config: MkDocsConfig, files: Files):
        """During this phase edit urls are set."""
        repo_url = config.get("repo_url", None)
        edit_uri = config.get("edit_uri", None)

        src_path = pathlib.PurePath(page.file.src_path).as_posix()
        if src_path in self._edit_paths:
            path = self._edit_paths.pop(src_path)
            if repo_url and edit_uri:
                # Ensure urljoin behavior is correct
                if not edit_uri.startswith(("?", "#")) and not repo_url.endswith("/"):
                    repo_url += "/"
                url = urllib.parse.urljoin(repo_url, edit_uri)
                page.edit_url = path and urllib.parse.urljoin(url, path)
        return html

    @event_priority(-100)
    def on_post_build(self, config: MkDocsConfig):
        self._dir.cleanup()

        if unused_edit_paths := {k: str(v) for k, v in self._edit_paths.items() if v}:
            msg = "mknodes: These set_edit_path invocations went unused: %r"
            logger.warning(msg, unused_edit_paths)
