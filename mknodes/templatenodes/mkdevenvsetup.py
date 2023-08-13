from __future__ import annotations

import logging

from typing import Any

from mknodes.basenodes import (
    mkadmonition,
    mkcode,
    mkcontainer,
    mkheader,
    mklink,
    mknode,
    mktext,
)
from mknodes.data import buildsystems
from mknodes.utils import helpers


logger = logging.getLogger(__name__)

EXAMPLE_URL = "http://www.some-github-provider.com/my-project.git"

START_TEXT = """All development for this library happens in the
{link} repo on GitHub.
First, you'll need to download the source code and install an
editable version of the Python package:"""

CLONE_CODE = """
# Clone the repository
git clone {repo_url}
cd {folder_name}
"""

PRE_COMMIT_CODE = """
# Setup pre-commit hooks for required formatting
pre-commit install
"""

PRE_COMMIT_TEXT = """This project uses `pre-commit` to ensure code quality.
A .pre-commit-config.yaml configuration file tailored for this project is provided
in the root folder."""

mkdocs_link = mklink.MkLink("http://www.mkdocs.org", "MkDocs")
material_link = mklink.MkLink(
    "https://squidfunk.github.io/mkdocs-material/",
    "Material for MkDocs",
)


def get_docs_section(project_name: str, docs_setup: str) -> list[mknode.MkNode]:
    return [
        mkheader.MkHeader("Docs Development"),
        mktext.MkText(f"{project_name} uses {docs_setup} to build the docs."),
        mktext.MkText("To build the docs:"),
        mkcode.MkCode("mkdocs build", language="bash"),
        mktext.MkText("To serve the docs locally at http://127.0.0.1:8000/:"),
        mkcode.MkCode("mkdocs serve", language="bash"),
        mktext.MkText("For additional mkdocs help and options:"),
        mkcode.MkCode("mkdocs --help", language="bash"),
    ]


def get_build_backend_section(backend: buildsystems.BuildSystem) -> list[mknode.MkNode]:
    backend_name = backend.identifier.capitalize()
    return [
        mkheader.MkHeader("Build system"),
        mktext.MkText(f"{backend_name} is used as the build system."),
        mkcode.MkCode(f"pip install {backend.identifier}", language="bash"),
        mklink.MkLink(backend.url, "More information"),
    ]


def get_pre_commit_section() -> list[mknode.MkNode]:
    return [
        mkheader.MkHeader("Pre-commit"),
        mktext.MkText(PRE_COMMIT_TEXT),
        mkcode.MkCode(PRE_COMMIT_CODE, language="md"),
        mkadmonition.MkAdmonition(
            [
                "To install pre-commit:",
                mkcode.MkCode("pip install pre-commit", language="bash"),
                mklink.MkLink("https://pre-commit.com", "More information"),
            ],
            collapsible=True,
            title="Installing pre-commit",
        ),
    ]


class MkDevEnvSetup(mkcontainer.MkContainer):
    """Text node containing Instructions to set up a dev environment."""

    ICON = "material/dev-to"
    STATUS = "new"

    def __init__(
        self,
        *,
        repo_url: str | None = None,
        use_pre_commit: bool | None = None,
        build_backend: buildsystems.BuildSystemStr | None = None,
        header: str = "Setting up a development environment",
        **kwargs: Any,
    ):
        """Constructor.

        Arguments:
            repo_url: Repo url to show. If None, it will be pulled from project.
            use_pre_commit: Show pre-commit install instructions.
                            If None, it will be pulled from project.
            build_backend: Build backend to show install instructions for.
                            If None, it will be pulled from project.
            header: Section header
            kwargs: Keyword arguments passed to parent
        """
        super().__init__(header=header, **kwargs)
        self._repo_url = repo_url
        self._use_pre_commit = use_pre_commit
        self._build_backend = build_backend

    def __repr__(self):
        return helpers.get_repr(
            self,
            repo_url=self._repo_url,
            use_pre_commit=self._use_pre_commit,
            build_backend=self._build_backend,
            _filter_empty=True,
        )

    @property
    def repo_url(self) -> str:
        match self._repo_url:
            case None if self.associated_project:
                repo_url = self.associated_project.repository_url or EXAMPLE_URL
            case str():
                repo_url = self._repo_url
            case _:
                repo_url = EXAMPLE_URL
        if not repo_url.endswith(".git"):
            repo_url += ".git"
        return repo_url

    @repo_url.setter
    def repo_url(self, value):
        self._repo_url = value

    @property
    def use_pre_commit(self) -> bool:  # type: ignore[return]
        match self._use_pre_commit:
            case None if self.associated_project:
                return self.associated_project.has_precommit()
            case bool():
                return self._use_pre_commit
            case None:
                return True
            case _:
                raise TypeError(self._use_pre_commit)

    @use_pre_commit.setter
    def use_pre_commit(self, value):
        self._use_pre_commit = value

    @property
    def build_backend(self) -> buildsystems.BuildSystem:  # type: ignore[return]
        match self._build_backend:
            case str():
                return buildsystems.BUILD_SYSTEMS[self._build_backend]
            case None if self.associated_project:
                return self.associated_project.pyproject.build_system
            case None:
                return buildsystems.setuptools
            case _:
                raise TypeError(self._build_backend)

    @build_backend.setter
    def build_backend(self, value):
        self._build_backend = value

    @property
    def items(self):
        folder_name = self.repo_url.removesuffix(".git").split("/")[-1]
        docs_str = " + ".join(str(i) for i in [mkdocs_link, material_link])
        code = CLONE_CODE.format(repo_url=self.repo_url, folder_name=folder_name)
        link = mklink.MkLink(self.repo_url, folder_name)
        start_text = START_TEXT.format(link=str(link))
        items = [mktext.MkText(start_text), mkcode.MkCode(code, language="md")]
        if self.use_pre_commit:
            items.extend(get_pre_commit_section())
        items.extend(get_build_backend_section(self.build_backend))
        items.extend(get_docs_section(docs_setup=docs_str, project_name=folder_name))
        for item in items:
            item.parent = self
        return items

    @items.setter
    def items(self, value):
        pass

    @staticmethod
    def create_example_page(page):
        import mknodes

        node = MkDevEnvSetup(header="")
        page += mknodes.MkReprRawRendered(node, header="### From project")
        node = MkDevEnvSetup(header="", repo_url="http://url_to_git_repo.com/name.git")
        page += mknodes.MkReprRawRendered(node, header="### Explicit")


if __name__ == "__main__":
    setup_text = MkDevEnvSetup(build_backend="flit")
    print(setup_text)
