from __future__ import annotations

import contextlib
import functools
import importlib
import os
import pathlib
import re

from mknodes.data import commitconventions, installmethods, taskrunners, tools
from mknodes.info import (
    contexts,
    # githubinfo,
    gitrepository,
    license,
    packageinfo,
    pyproject,
)
from mknodes.utils import log, packagehelpers, pathhelpers, reprhelpers, yamlhelpers


logger = log.get_logger(__name__)


SOCIALS = {
    "gitter.im": "fontawesome/brands/gitter",
    "matrix.to": "fontawesome/brands/gitter",
    "twitter.com": "fontawesome/brands/twitter",
    "docker.com": "fontawesome/brands/docker",
    "fosstodon.org": "fontawesome/brands/mastodon",
    "discord.gg": "fontawesome/brands/discord",
    "linkedin.com": "fontawesome/brands/linkedin",
    "dev.to": "fontawesome/brands/dev",
    "medium.to": "fontawesome/brands/medium",
}


GITHUB_REGEX = re.compile(
    r"(?:http?:\/\/|https?:\/\/)?"
    r"(?:www\.)?"
    r"github\.com\/"
    r"(?:\/*)"
    r"([\w\-\.]*)\/"
    r"([\w\-]*)"
    r"(?:\/|$)?"  # noqa: COM812
)


class FolderInfo:
    """Aggregates information about a working dir."""

    def __init__(self, path: str | os.PathLike | None = None):
        self.path = pathlib.Path(path or ".")
        self.pyproject = pyproject.PyProject(self.path)
        # packagehelpers.install_or_import(mod_name)
        self.git = gitrepository.GitRepository(self.path)
        self.mkdocs_config = {}
        if (path := self.path / "mkdocs.yml").exists():
            text = path.read_text(encoding="utf-8")
            with contextlib.suppress(yamlhelpers.YAMLError):
                # TODO: cannot load some remote mkdocs configs
                # (for example from pymdown-extensions)
                self.mkdocs_config = yamlhelpers.load_yaml(text, mode="unsafe")
        # self.github = githubinfo.GitHubRepo(
        #     self.repository_username,
        #     self.repository_name,
        # )
        self._temp_directory = None

    @property
    def module(self):
        mod_name = packagehelpers.distribution_to_package(self.git.repo_name)
        mod_name = mod_name.replace("-", "_").lower()
        return importlib.import_module(mod_name)

    def __repr__(self):
        return reprhelpers.get_repr(self, path=self.path)

    @classmethod
    def clone_from(
        cls,
        url: str,
        # path: str | os.PathLike,
        depth: int = 100,
    ):
        import tempfile

        import git

        directory = tempfile.TemporaryDirectory(prefix="mknodes_repo_")
        logger.info("Created temporary directory %s", directory.name)
        logger.info("Cloning %s with depth %s", url, depth)
        repo = git.Repo.clone_from(url, directory.name, depth=depth)
        logger.info("Finished cloning.")
        kls = cls(repo.working_dir)
        kls._temp_directory = directory
        return kls

    @property
    def info(self):
        return packageinfo.get_info(self.pyproject.name or self.git.repo_name)

    @property
    def repository_url(self) -> str:
        if url := self.mkdocs_config.get("repo_url"):
            return url
        if url := self.git.repo_url:
            return url
        if url := self.info.repository_url:
            return url
        msg = "Could not find any repository url"
        raise RuntimeError(msg)

    @property
    def repository_username(self) -> str:
        if match := GITHUB_REGEX.match(self.repository_url or ""):
            return match.group(1)
        msg = "Could not detect repository username"
        raise RuntimeError(msg)

    @property
    def repository_name(self) -> str:
        if match := GITHUB_REGEX.match(self.repository_url or ""):
            return match.group(2)
        msg = "Could not detect repository name"
        raise RuntimeError(msg)

    @property
    def inventory_url(self) -> str | None:
        """Return best guess for a link to an inventory file."""
        if url := self.mkdocs_config.get("site_url"):
            return f"{url.rstrip('/')}/objects.inv"
        return None

    @property
    def package_name(self) -> str:
        return self.info.package_name

    @property
    def package_repos(self) -> list[installmethods.InstallMethodStr]:
        return self.pyproject.package_repos

    @property
    def commit_types(self) -> list[commitconventions.CommitTypeStr]:
        return self.pyproject.allowed_commit_types

    @property
    def tools(self) -> list[tools.Tool]:
        """Return a list of build tools used by this package."""
        return [t for t in tools.TOOLS.values() if t.is_used(self)]

    @functools.cached_property
    def license_file_path(self) -> pathlib.Path | None:
        """Return license file path (relative to project root) from metadata."""
        for path in ["LICENSE", "LICENSE.md", "LICENSE.txt"]:
            if (file := self.path / path).exists():
                return file
        if file := self.info.metadata.json.get("license_file"):
            return self.path / file if isinstance(file, str) else self.path / file[0]
        return None

    @functools.cached_property
    def license_text(self) -> str | None:
        if self.license_file_path:
            return self.license_file_path.read_text(encoding="utf-8")
        if license_name := self.info.license_name:
            lic = license.License.from_name(license_name)
            lic.resolve_by_distribution(self.info.name)
            return lic.content
        return None

    @property
    def social_info(self) -> list[dict[str, str]]:
        result = []
        if self.repository_url:
            result.append(
                dict(icon="fontawesome/brands/github", link=self.repository_url),
            )
        for link in self.info.urls.values():
            result.extend(
                dict(icon=v, link=link) for k, v in SOCIALS.items() if k in link
            )
        result.append(
            dict(
                icon="fontawesome/brands/python",
                link=f"https://pypi.org/project/{self.module.__name__}/",
            ),
        )
        return result

    @property
    def task_runners(self) -> list[taskrunners.TaskRunner]:
        """Return list of task runners used by this package."""
        return [
            runner
            for runner in taskrunners.TASK_RUNNERS.values()
            if any(
                pathhelpers.find_file_in_folder_or_parent(i, self.path)
                for i in runner.filenames
            )
        ]

    def aggregate_info(self) -> dict:
        infos = dict(
            repository_name=self.repository_name,
            repository_username=self.repository_username,
            repository_url=self.repository_url,
            social_info=self.social_info,
            author_name=self.info.author_name,
            author_email=self.info.author_email,
        )
        infos |= self.info.metadata.json
        if self.mkdocs_config:
            infos["name"] = self.mkdocs_config["site_name"]
        return infos

    @property
    def context(self):
        return contexts.PackageContext(
            pretty_name=self.mkdocs_config.get("site_name") or self.info.name,
            distribution_name=self.info.name,
            author_name=self.info.author_name,
            author_email=self.info.author_email,
            description=self.info.metadata["Description"],
            summary=self.info.metadata["Summary"],
            authors=self.info.authors,
            classifiers=self.info.classifiers,
            classifier_map=self.info.classifier_map,
            keywords=self.info.keywords,
            license_name=self.info.license_name,
            required_python_version=self.info.required_python_version,
            required_package_names=self.info.required_package_names,
            extras=self.info.extras,
            entry_points=self.info.get_entry_points(),
            mkdocs_config=self.mkdocs_config,
            social_info=self.social_info,
            repository_url=self.repository_url,
            inventory_url=self.inventory_url,
            task_runners=self.task_runners,
            build_system=self.pyproject.build_system,
            configured_build_systems=self.pyproject.configured_build_systems,
            tools=self.pyproject.tool,
            commit_types=self.pyproject.allowed_commit_types,
            extras_descriptions=self.pyproject.extras_descriptions,
            package_repos=self.pyproject.package_repos,
        )


if __name__ == "__main__":
    info = FolderInfo.clone_from("https://github.com/mkdocs/mkdocs.git")
    print(info.inventory_url)
