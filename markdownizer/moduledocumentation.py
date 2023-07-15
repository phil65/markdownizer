from __future__ import annotations

import contextlib
import importlib
import inspect
import logging
import pathlib
import types

from markdownizer import classhelpers, nav, table, mkpage


logger = logging.getLogger(__name__)


class ModuleDocumentation(nav.Nav):
    def __init__(
        self,
        module: types.ModuleType | str,
        exclude_modules: list[str] | None = None,
        **kwargs,
    ):
        self.module = classhelpers.to_module(module)
        self.is_package = hasattr(self.module, "__path__")
        self.module_name = self.module.__name__
        self.module_path = self.module.__file__
        super().__init__(section=self.module_name)
        self._exclude = exclude_modules or []
        self.root_path = pathlib.Path(f"./{self.module_name}")

    def iter_files(self, glob: str = "*/*.py"):
        for path in sorted(self.root_path.rglob(glob)):
            if (
                all(i not in path.parts for i in self._exclude)
                and not any(i.startswith("__") for i in path.parent.parts)
                and not path.is_dir()
            ):
                yield path.relative_to(self.root_path)

    def iter_classes(
        self,
        submodule: types.ModuleType | str | tuple | list | None = None,
        recursive: bool = False,
        filter_by___all__: bool = False,
        _seen=None,
    ):
        mod = classhelpers.to_module(submodule) if submodule else self.module
        if mod is None:
            return
        if recursive:
            seen = _seen or set()
            for _submod_name, submod in inspect.getmembers(mod, inspect.ismodule):
                if submod.__name__.startswith(self.module_name) and submod not in seen:
                    seen.add(submod)
                    yield from self.iter_classes(submod, recursive=True, _seen=seen)
        for klass_name, klass in inspect.getmembers(mod, inspect.isclass):
            if filter_by___all__ and (
                not hasattr(mod, "__all__") or klass_name not in mod.__all__
            ):
                continue
            if klass.__module__.startswith(self.module_name):
                yield klass

    def iter_modules_for_glob(self, glob="*/*.py"):
        for path in self.iter_files(glob):
            module_path = path.with_suffix("")
            parts = tuple(module_path.parts)
            complete_module_path = f"{self.module_name}." + ".".join(parts)
            with contextlib.suppress(ImportError, AttributeError):
                yield importlib.import_module(complete_module_path)

    def iter_classes_for_glob(
        self, glob="*/*.py", recursive: bool = False, avoid_duplicates: bool = True
    ):
        """Yields (class, path) tuples."""
        seen = set()
        for path in self.iter_files(glob):
            module_path = path.with_suffix("")
            parts = tuple(self.module_name, *module_path.parts)
            module = classhelpers.to_module(parts)
            if not module:
                return
            for klass in self.iter_classes(module, recursive=recursive):
                if (klass, path) not in seen or not avoid_duplicates:
                    seen.add((klass, path))
                    yield klass, path

    def add_overview_page(self, predicate: Callable | None = None):
        page = mkpage.MkPage(
            hide_toc=True,
            path=pathlib.Path(self.section, "index.md"),
            # parent=self,
        )
        # page += self.get_dependency_table()
        page += table.Table.get_module_overview(
            self.module_name, predicate=predicate
        )
        return page

    def add_class_page(self, klass, **kwargs):
        parts = classhelpers.get_topmost_module_path_for_klass(klass).split(".")
        # parts = klass.__module__.split(".")
        path = pathlib.Path(f"{klass.__name__}.md")
        page = mkpage.ClassPage(
            klass=klass,
            module_path=parts,
            path=path,
            parent=self,
            **kwargs,
        )
        self[(*parts, klass.__name__)] = path.with_name(f"{klass.__name__}.md")
        self.pages.append(page)
        return page

    def add_module_page(self, module, path, **kwargs):
        path = pathlib.Path(path)
        complete_mod_path = f"{self.module_name}.{module}"
        parts = path.parts[:-1]
        page = mkpage.ModulePage(
            hide_toc=True,
            module=complete_mod_path,
            path=pathlib.Path(self.section, path),
            parent=self,
            **kwargs,
        )
        self[parts] = path.with_name("index.md")
        self.pages.append(page)
        return page

    def get_dependency_table(self) -> table.Table:
        return table.DependencyTable(self.module_name)

    def add_dependency_page(self, path: str | os.PathLike, **kwargs):
        page = mkpage.MkPage(path=path, parent=parent, **kwargs)
        page.parent_item = self
        page += self.get_dependency_table()
        self.pages.append(page)
        path = pathlib.Path(path)
        parts = path.parts[:-1]
        self[parts] = path.with_name("dependencies.md")
        return page


if __name__ == "__main__":
    doc = ModuleDocumentation(module="mkdocs")
    page = doc.add_overview_page()
    print(page)
