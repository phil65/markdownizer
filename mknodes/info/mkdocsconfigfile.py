from __future__ import annotations

from mknodes.info import yamlfile


class MkDocsConfigFile(yamlfile.YamlFile):
    @property
    def theme(self):
        return self.get_section("theme")

    @property
    def markdown_extensions(self):
        return self.get_section("markdown_extensions")

    @property
    def plugins(self):
        return self.get_section("plugins")

    @property
    def mknodes_config(self):
        return self.get_section("plugins", "mknodes")

    @property
    def mkdocstrings_config(self):
        return self.get_section("plugins", "mkdocstrings", "handlers", "python")

    def update_mknodes_section(
        self,
        repo_url: str | None = None,
        build_fn: str | None = None,
        clone_depth: int | None = None,
    ):
        for plugin in self._data["plugins"]:
            if "mknodes" in plugin:
                if repo_url is not None:
                    plugin["mknodes"]["repo_path"] = repo_url
                if build_fn is not None:
                    plugin["mknodes"]["build_fn"] = build_fn
                if clone_depth is not None:
                    plugin["mknodes"]["clone_depth"] = clone_depth


if __name__ == "__main__":
    info = MkDocsConfigFile("mkdocs.yml")
    print(info.mkdocstrings_config)
