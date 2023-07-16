"""Generate the code reference pages and navigation."""

from __future__ import annotations

import pathlib
import pprint

import markdownizer
from markdownizer import classhelpers, utils

import mkdocs

root_nav = markdownizer.Nav()

home_nav = root_nav.add_nav("Home")

intro_page = home_nav.add_page("Introduction", hide_toc=True)
intro_page += "### Not in the mood to write documentation? Let´s code it then!"
intro_page.add_admonition(
    "API is still evolving, so consider this a preview.", typ="danger", title="Warning!"
)
intro_page += "This is the source code for building this website:"
intro_page.add_code(pathlib.Path(__file__).read_text(), language="py")


# now lets create the documentation. This is the "manual way" by building custom pages.
nodes_nav = home_nav.add_nav("Nodes")
# Basically everything interesting in this library inherits from MarkdownNode.
# It´s the base class for all tree nodes we are building. The tree goes from the root nav
# down to single markup elements.
# get_subclasses just calls __subclasses__ recursively.
for kls in classhelpers.get_subclasses(markdownizer.MarkdownNode):
    subpage = nodes_nav.add_page(kls.__name__)
    if hasattr(kls, "examples"):
        # "examples()" yields dicts with constructor keyword arguments for building examples.
        for i, sig in enumerate(kls.examples(), start=1):
            subpage += f"## Example {i} for class {kls.__name__!r}\n"
            sig_txt = utils.format_kwargs(sig)
            text = (
                f"node = markdownizer.{kls.__name__}({sig_txt})\n"
                + "str(node)  # or node.to_markdown()"
            )
            subpage += markdownizer.Code(
                language="py", code=text, title=f"example_{i}.py"
            )
            node = kls(**sig)
            code = markdownizer.Code(
                language="markdown", code=node, title=f"result_{i}.md"
            )
            tabs = {"Generated markdown": str(code), "Preview": str(node)}
            subpage += markdownizer.Tabbed(tabs)
            subpage.add_newlines(3)
    subpage.add_mkdocstrings(kls)

# We could also add docs for random other modules, too. This is the "semi-automated" way.
mkdocs_docs = root_nav.add_documentation(module=mkdocs)
for klass in mkdocs_docs.iter_classes(recursive=True):
    mkdocs_docs.add_class_page(klass=klass)

# Lets show some info about the tree we built.
# The tree starts from the root nav down to the Markup elements.
tree_page = home_nav.add_page("Node tree", hide_toc=True)
lines = [f"{indent * '    '} {repr(node)}" for indent, node in root_nav.yield_nodes()]
tree_page += markdownizer.Code(language="py", code="\n".join(lines))
virtual_files = root_nav.all_virtual_files()
files_page = home_nav.add_page("File map", hide_toc=True)
files_page += markdownizer.Code(language="py", code=pprint.pformat(virtual_files))


root_nav.write()  # Finally, we write the whole tree.
