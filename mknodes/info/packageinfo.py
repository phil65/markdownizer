from __future__ import annotations

import contextlib
import functools
import logging

from typing import Literal

from mknodes.utils import packagehelpers, reprhelpers


logger = logging.getLogger(__name__)


ClassifierStr = Literal[
    "Development Status",
    "Environment",
    "Framework",
    "Intended Audience",
    "License",
    "Natural Language",
    "Operating System",
    "Programming Language",
    "Topic",
    "Typing",
]

CLASSIFIERS: list[ClassifierStr] = [
    "Development Status",
    "Environment",
    "Framework",
    "Intended Audience",
    "License",
    "Natural Language",
    "Operating System",
    "Programming Language",
    "Topic",
    "Typing",
]


registry: dict[str, PackageInfo] = {}


def get_info(mod_name: str) -> PackageInfo:
    mapping = packagehelpers.get_package_map()
    pkg_name = mapping[mod_name][0] if mod_name in mapping else mod_name
    if mod_name not in registry:
        registry[mod_name] = PackageInfo(pkg_name)
    return registry[mod_name]


class PackageInfo:
    def __init__(self, pkg_name: str):
        self.package_name = pkg_name
        self.distribution = packagehelpers.get_distribution(pkg_name)
        logger.info("Loaded package info: '%s'", pkg_name)
        self.metadata = packagehelpers.get_metadata(self.distribution)
        self.urls = {
            v.split(",")[0].strip(): v.split(",")[1].strip()
            for k, v in self.metadata.items()
            if k == "Project-URL"
        }
        if "Home-page" in self.metadata:
            self.urls["Home-page"] = self.metadata["Home-page"].strip()
        self.classifiers = [v for h, v in self.metadata.items() if h == "Classifier"]
        self.version = self.metadata["Version"]
        self.metadata_version = self.metadata["Metadata-Version"]
        self.name = self.metadata["Name"]

    def __repr__(self):
        return reprhelpers.get_repr(self, pkg_name=self.package_name)

    def __hash__(self):
        return hash(self.package_name)

    @property
    def inventory_url(self) -> str | None:
        """Return best guess for a link to an inventory file."""
        for v in self.urls.values():
            if "github.io" in v or "readthedocs" in v:
                return f"{v.rstrip('/')}/objects.inv"
        if url := self.urls.get("Documentation"):
            return f"{url.rstrip('/')}/objects.inv"
        return None

    @functools.cached_property
    def _required_deps(self) -> list[packagehelpers.Dependency]:
        requires = packagehelpers.get_requires(self.distribution)
        return [packagehelpers.get_dependency(i) for i in requires] if requires else []

    @property
    def license_name(self) -> str | None:
        """Get name of the license."""
        if license_name := self.metadata.get("License-Expression", "").strip():
            return license_name
        return next(
            (
                value.rsplit("::", 1)[1].strip()
                for header, value in self.metadata.items()
                if header == "Classifier" and value.startswith("License ::")
            ),
            None,
        )

    @property
    def repository_url(self) -> str | None:
        """Return repository URL from metadata."""
        return next(
            (
                self.urls[tag]
                for tag in ["Source", "Repository", "Source Code"]
                if tag in self.urls
            ),
            None,
        )

    @property
    def homepage(self) -> str | None:
        if "Home-page" in self.urls:
            return self.urls["Home-page"]
        if "Homepage" in self.urls:
            return self.urls["Homepage"]
        if "Documentation" in self.urls:
            return self.urls["Documentation"]
        return self.repository_url

    @property
    def keywords(self) -> list[str]:
        """Return a list of keywords from metadata."""
        return self.metadata.get("Keywords", "").split(",")

    @property
    def classifier_map(self) -> dict[str, list[str]]:
        """Return a dict containing the classifier categories and values from metadata.

        {category_1: [classifier_1, ...],
         category_2, [classifier_x, ...],
         ...
         }
        """
        classifiers: dict[str, list[str]] = {}
        for k, v in self.metadata.items():
            if k == "Classifier":
                category, value = v.split(" :: ", 1)
                if category in classifiers:
                    classifiers[category].append(value)
                else:
                    classifiers[category] = [value]
        return classifiers

    @property
    def required_package_names(self) -> list[str]:
        """Get a list of names from required packages."""
        return [i.name for i in self._required_deps]

    @property
    def author_email(self) -> str:
        mail = self.metadata["Author-email"].split(" ")[-1]
        return mail.replace("<", "").replace(">", "")

    @property
    def author_name(self) -> str:
        return self.metadata["Author-email"].rsplit(" ", 1)[0]

    @property
    def authors(self) -> dict[str, str]:
        """Return a dict containing the authors.

        {author 1: email of author 1,
         author_2, email of author 2,
         ...
         }
        """
        authors: dict[str, str] = {}
        for k, v in self.metadata.items():
            if k == "Author-email":
                mail = v.split(" ")[-1]
                mail = mail.replace("<", "").replace(">", "")
                name = v.rsplit(" ", 1)[0]
                authors[name] = mail
        return authors

    @property
    def extras(self) -> dict[str, list[str]]:
        """Return a dict containing extras and the packages {extra: [package_1, ...]}."""
        extras: dict[str, list[str]] = {}
        for dep in self._required_deps:
            for extra in dep.extras:
                if extra in extras:
                    extras[extra].append(dep.name)
                else:
                    extras[extra] = [dep.name]
        return extras

    @property
    def required_python_version(self) -> str | None:
        return self.metadata.json.get("requires_python")

    @property
    def required_packages(self) -> dict[PackageInfo, packagehelpers.Dependency]:
        modules = (
            {
                packagehelpers.get_dependency(i).name
                for i in packagehelpers.get_requires(self.distribution)
            }
            if packagehelpers.get_requires(self.distribution)
            else set()
        )
        packages = {}
        for mod in modules:
            with contextlib.suppress(Exception):
                packages[get_info(mod)] = self._get_dep_info(mod)
        return packages

    def _get_dep_info(self, name: str) -> packagehelpers.Dependency:
        for i in self._required_deps:
            if i.name == name:
                return i
        raise ValueError(name)

    def get_entry_points(
        self,
        group: str | None = None,
    ) -> dict[str, packagehelpers.EntryPoint]:
        return packagehelpers.get_entry_points(self.distribution, group=group)


if __name__ == "__main__":
    info = get_info("mknodes")
    print(info.get_entry_points("mkdocs.plugins"))
    print(info.metadata.json)
