from __future__ import annotations

from collections.abc import MutableMapping
import logging
import os

from typing import Generic, TypeVar

import mergedeep

from mknodes import mknav
from mknodes.info import folderinfo
from mknodes.pages import pagetemplate
from mknodes.plugin import infocollector
from mknodes.theme import theme as theme_
from mknodes.utils import helpers, linkprovider, reprhelpers, requirements


logger = logging.getLogger(__name__)


T = TypeVar("T", bound=theme_.Theme)


class Project(Generic[T]):
    """MkNodes Project."""

    def __init__(
        self,
        theme: T,
        base_url: str = "",
        use_directory_urls: bool = True,
        repo_path: str | os.PathLike | None = None,
    ):
        self.linkprovider = linkprovider.LinkProvider(
            base_url=base_url,
            use_directory_urls=use_directory_urls,
            include_stdlib=True,
        )
        self.theme: T = theme
        self.templates = self.theme.templates
        self.error_page: pagetemplate.PageTemplate = self.templates["404.html"]
        if helpers.is_url(str(repo_path)):
            self.folderinfo = folderinfo.FolderInfo.clone_from(str(repo_path))
        else:
            self.folderinfo = folderinfo.FolderInfo(repo_path)
        self._root: mknav.MkNav | None = None
        self.infocollector = infocollector.InfoCollector(load_templates=True)

    def __repr__(self):
        return reprhelpers.get_repr(self, repo_path=str(self.folderinfo.path))

    @classmethod
    def for_mknodes(cls) -> Project:
        from mknodes import mkdocsconfig

        config = mkdocsconfig.Config()
        theme = theme_.Theme.get_theme(config)
        return cls(
            base_url=config.site_url or "",
            use_directory_urls=config.use_directory_urls,
            theme=theme,
        )

    @property
    def info(self):
        return self.folderinfo.info

    @property
    def package_name(self) -> str:
        return self.folderinfo.package_name

    def get_root(self, **kwargs) -> mknav.MkNav:
        self._root = mknav.MkNav(project=self, **kwargs)
        return self._root

    def get_requirements(self) -> requirements.Requirements:
        reqs = dict(self._root.get_requirements()) if self._root else {}
        reqs = mergedeep.merge(reqs, dict(self.theme.get_requirements()))
        self.theme.adapt_extensions(reqs["markdown_extensions"])
        reqs["markdown_extensions"]["pymdownx.magiclink"] = dict(
            repo_url_shorthand=True,
            user=self.folderinfo.repository_username,
            repo=self.folderinfo.repository_name,
        )
        return requirements.Requirements(**reqs)

    def set_root(self, nav: mknav.MkNav):
        self._root = nav
        nav.associated_project = self

    def all_files(self) -> dict[str, str | bytes]:
        files = self._root.all_virtual_files() if self._root else {}
        return files | self.theme.get_files()

    def all_css(self) -> dict[str, str]:
        css = self.theme.get_requirements().css
        if self._root:
            css |= self._root.get_requirements().css
        return css

    def all_templates(self) -> list[pagetemplate.PageTemplate]:
        templates = self.theme.get_requirements().templates[:]
        if self._root:
            templates.extend(self._root.get_requirements().templates)
        return templates

    def all_markdown_extensions(self) -> MutableMapping[str, dict]:
        extensions = (
            self._root.get_requirements().markdown_extensions if self._root else {}
        )
        self.theme.adapt_extensions(extensions)
        extensions["pymdownx.magiclink"] = dict(
            repo_url_shorthand=True,
            user=self.folderinfo.repository_username,
            repo=self.folderinfo.repository_name,
        )
        return extensions

    def aggregate_info(self):
        self.infocollector.get_info_from_project(self)


if __name__ == "__main__":
    project = Project.for_mknodes()
    print(project.get_requirements())
