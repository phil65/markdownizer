from __future__ import annotations

import contextlib
import functools

from importlib import metadata
import pathlib
import re

from packaging.markers import Marker
from packaging.requirements import Requirement

from mknodes.utils import helpers


GITHUB_REGEX = re.compile(
    r"(?:http?:\/\/|https?:\/\/)?"
    r"(?:www\.)?"
    r"github\.com\/"
    r"(?:\/*)"
    r"([\w\-\.]*)\/"
    r"([\w\-]*)"
    r"(?:\/|$)?"  # noqa: COM812
)

CLASSIFIERS = [
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


def get_extras(markers: list) -> list[str]:
    extras = []
    for marker in markers:
        match marker:
            case list():
                extras.extend(get_extras(marker))
            case tuple():
                if str(marker[0]) == "extra":
                    extras.append(str(marker[2]))
    return extras


class Dependency:
    def __init__(self, name: str):
        self.req = Requirement(name)
        self.name = self.req.name
        self.marker = Marker(name.split(";", maxsplit=1)[-1]) if ";" in name else None
        self.extras = get_extras(self.marker._markers) if self.marker else []

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name!r})"


@functools.cache
def get_distribution(name):
    return metadata.distribution(name)


@functools.cache
def get_metadata(dist):
    return dist.metadata


@functools.cache
def get_requires(dist):
    return dist.requires


@functools.cache
def get_dependency(name):
    return Dependency(name)


registry: dict[str, PackageInfo] = {}


def get_info(pkg_name):
    if pkg_name in registry:
        return registry[pkg_name]
    registry[pkg_name] = PackageInfo(pkg_name)
    return registry[pkg_name]


class PackageInfo:
    def __init__(self, pkg_name: str):
        self.package_name = pkg_name
        self.distribution = get_distribution(pkg_name)
        self.metadata = get_metadata(self.distribution)
        self.urls = {
            v.split(",")[0]: v.split(",")[1]
            for k, v in self.metadata.items()
            if k == "Project-URL"
        }
        requires = get_requires(self.distribution)
        self.required_deps = [get_dependency(i) for i in requires] if requires else []
        self.classifiers = [v for h, v in self.metadata.items() if h == "Classifier"]
        self.version = self.metadata["Version"]
        self.metadata_version = self.metadata["Metadata-Version"]
        self.name = self.metadata["Name"]

    def __repr__(self):
        return helpers.get_repr(self, pkg_name=self.package_name)

    def __hash__(self):
        return hash(self.package_name)

    def get_license(self) -> str:
        """Get name of the license."""
        if license_name := self.metadata.get("License-Expression", "").strip():
            return license_name
        return next(
            (
                value.rsplit("::", 1)[1].strip()
                for header, value in self.metadata.items()
                if header == "Classifier" and value.startswith("License ::")
            ),
            "Unknown",
        )

    def get_license_file_path(self) -> pathlib.Path | None:
        """Return license file path (relative to project root) from metadata."""
        file = self.metadata.get("License-File")
        return pathlib.Path(file) if file else None

    def get_repository_url(self) -> str | None:
        """Return repository URL from metadata."""
        if "Source" in self.urls:
            return self.urls["Source"]
        return self.urls["Repository"] if "Repository" in self.urls else None

    def get_repository_username(self) -> str | None:
        """Try to extract repository username from metadata."""
        if match := GITHUB_REGEX.match(self.get_repository_url() or ""):
            return match.group(1)
        return None

    def get_repository_name(self) -> str | None:
        """Try to extract repository name from metadata."""
        if match := GITHUB_REGEX.match(self.get_repository_url() or ""):
            return match.group(2)
        return None

    def get_keywords(self) -> list[str]:
        """Return a list of keywords from metadata."""
        return self.metadata.get("Keywords", "").split(",")

    def get_classifiers(self) -> dict[str, list[str]]:
        """Return a dict containing the classifier categories and values from metadata.

        {category_1: [classifier_1, ...],
         category_2, [classifier_x, ...],
         ...
         }
        """
        classifiers: dict[str, list[str]] = {}
        for k, v in self.metadata.items():
            if k == "Classifier":
                category = v.split(" :: ")[0]
                value = v.split(" :: ", 1)[1]
                if category in classifiers:
                    classifiers[category].append(value)
                else:
                    classifiers[category] = [value]
        return classifiers

    def get_required_package_names(self) -> list[str]:
        """Get a list of names from required packages."""
        return [i.name for i in self.required_deps]

    def get_required_packages(self) -> dict[PackageInfo, Dependency]:
        modules = (
            {Requirement(i).name for i in get_requires(self.distribution)}
            if get_requires(self.distribution)
            else set()
        )
        packages = {}
        for mod in modules:
            with contextlib.suppress(Exception):
                packages[get_info(mod)] = self.get_dep_info(mod)
        return packages

    def get_dep_info(self, name: str) -> Dependency:
        for i in self.required_deps:
            if i.name == name:
                return i
        raise ValueError(name)

    def get_extras(self) -> dict[str, list[str]]:
        """Return a dict containing extras and the packages {extra: [package_1, ...]}."""
        extras: dict[str, list[str]] = {}
        for dep in self.required_deps:
            for extra in dep.extras:
                if extra in extras:
                    extras[extra].append(dep.name)
                else:
                    extras[extra] = [dep.name]
        return extras

    def get_author_email(self) -> str:
        mail = self.metadata["Author-Email"].split(" ")[-1]
        return mail.replace("<", "").replace(">", "")

    def get_author_name(self) -> str:
        return self.metadata["Author-Email"].rsplit(" ", 1)[0]


if __name__ == "__main__":
    info = get_info("mknodes")
    print(info.get_author_name())
