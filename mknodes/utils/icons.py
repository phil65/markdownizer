from __future__ import annotations

from collections.abc import Sequence
import functools

from typing import Any, Literal
import xml.etree.ElementTree as etree

from mknodes import paths


PYCONIFY_TO_PREFIXES = {
    "mdi": "material",
    "simple-icons": "simple",
    "octicon": "octicons",
    "fa-regular": "fontawesome-regular",
    "fa-brands": "fontawesome-brands",
    "fa-solid": "fontawesome-solid",
}

Rotation = Literal["90", "180", "270", 90, 180, 270, "-90", 1, 2, 3]
Flip = Literal["horizontal", "vertical", "horizontal,vertical"]


@functools.cache
def _get_collection_map(*prefixes: str) -> dict[str, list[str]]:
    """Return a dictionary with a mapping from pyconify name to icon prefixes.

    In order to provide compatibility with the materialx-icon-index,
    we also add the prefixes used by that index, which is different from
    the pyconify prefixes. (material vs mdi etc, see PYCONIFY_TO_PREFIXES)
    """
    import pyconify

    mapping = {coll: [coll] for coll in pyconify.collections(*prefixes)}
    for k, v in PYCONIFY_TO_PREFIXES.items():
        if k in mapping:
            mapping[k].append(v)
    return mapping


def _get_pyconify_icon_index(*collections: str) -> dict[str, dict[str, str]]:
    """Return a icon index for the pymdownx emoji extension containing pyconify icons.

    The dictionaries contain two key-value pairs:
    "name" is the emoji identifier,
    "path" is the pyconify key

    """
    import pyconify

    index = {}
    for coll, prefixes in _get_collection_map(*collections).items():
        collection = pyconify.collection(coll)
        for icon_name in collection.get("uncategorized", []):
            for prefix in prefixes:
                name = f":{prefix}-{icon_name}:"
                index[name] = {
                    "name": name,
                    "path": f"{coll}:{icon_name}",
                    "set": coll,
                }
        for cat in pyconify.collection(coll).get("categories", {}).values():
            for icon_name in cat:
                for prefix in prefixes:
                    name = f":{prefix}-{icon_name}:"
                    index[name] = {
                        "name": name,
                        "path": f"{coll}:{icon_name}",
                        "set": coll,
                    }
    return index


@functools.cache
def _patch_index_with_sets(icon_sets: Sequence[str]) -> dict[str, Any]:
    from pymdownx import twemoji_db

    # Copy the Twemoji index
    index = {
        "name": "twemoji",
        "emoji": twemoji_db.emoji,
        "aliases": twemoji_db.aliases,
    }
    # icons = _get_pyconify_icon_index(*icon_sets)
    icons = load_icon_index()
    index["emoji"].update(icons)
    return index


def twemoji(options: dict[str, Any], md) -> dict[str, Any]:
    """Provide a copied Twemoji index with additional codes for Pyconify icons."""
    default = list(PYCONIFY_TO_PREFIXES.keys())
    icon_sets = options.get("icon_sets", default)[:]
    return _patch_index_with_sets(tuple(icon_sets))


def to_svg(index, shortname, alias, uc, alt, title, category, options, md):
    """Return SVG element."""
    from pymdownx.emoji import TWEMOJI_SVG_CDN, add_attributes

    is_unicode = uc is not None
    if is_unicode:
        image_path = options.get("image_path", TWEMOJI_SVG_CDN)
        attributes = {
            "class": options.get("classes", index),
            "alt": alt,
            "src": f"{image_path}{uc}.svg",
        }

        if title:
            attributes["title"] = title

        add_attributes(options, attributes)

        return etree.Element("img", attributes)
    el = etree.Element("span", {"class": options.get("classes", index)})
    svg_path = md.inlinePatterns["emoji"].emoji_index["emoji"][shortname]["path"]
    svg = get_icon_svg(svg_path)
    el.text = md.htmlStash.store(svg)
    return el


def get_icon_svg(
    icon: str,
    color: str | None = None,
    height: str | int | None = None,
    width: str | int | None = None,
    flip: Flip | None = None,
    rotate: Rotation | None = None,
    box: bool | None = None,
) -> str:
    """Return svg for given pyconify icon key.

    Key should look like "mdi:file"
    For compatibility, this method also supports compatibility for
    emoji-slugs (":material-file:") as well as material-paths ("material/file")

    If no group is supplied as part of the string, mdi is assumed as group:

    Arguments:
        icon: Pyconify icon name
        color: Icon color. Replaces currentColor with specific color, resulting in icon
               with hardcoded palette.
        height: Icon height. If only one dimension is specified, such as height, other
                dimension will be automatically set to match it.
        width: Icon width. If only one dimension is specified, such as height, other
               dimension will be automatically set to match it.
        flip: Flip icon.
        rotate: Rotate icon. If an integer is provided, it is assumed to be in degrees.
        box: Adds an empty rectangle to SVG that matches the icon's viewBox. It is needed
            when importing SVG to various UI design tools that ignore viewBox. Those
            tools, such as Sketch, create layer groups that automatically resize to fit
            content. Icons usually have empty pixels around icon, so such software crops
            those empty pixels and icon's group ends up being smaller than actual icon,
            making it harder to align it in design.

    Example:
        get_icon_svg("file")  # implicit mdi group
        get_icon_svg("mdi:file")  # pyconify key
        get_icon_svg("material/file")  # Material-style path
        get_icon_svg(":material-file:")  # material-style emoji slug
    """
    key = get_pyconify_key(icon)
    import pyconify

    return pyconify.svg(
        key,
        color=color,
        height=height,
        width=width,
        flip=flip,
        rotate=rotate,
        box=box,
    ).decode()


def get_pyconify_key(icon: str) -> str:
    for k, v in PYCONIFY_TO_PREFIXES.items():
        path = f'{v.replace("-", "/")}/'
        icon = icon.replace(path, f"{k}:")
        icon = icon.replace(f":{v}-", f"{k}:")
    icon = icon.strip(":")
    mapping = {k: v[0] for k, v in _get_collection_map().items()}
    for prefix in mapping:
        if icon.startswith(f"{prefix}-"):
            icon = icon.replace(f"{prefix}-", f"{prefix}:")
            break
    if (count := icon.count(":")) > 1:
        icon = icon.replace(":", "-", count - 1)
    if ":" not in icon:
        icon = f"mdi:{icon}"
    return icon


def get_emoji_slug(icon: str) -> str:
    return f":{get_pyconify_key(icon).replace(':', '-')}:"


def get_icon_xml(icon: str) -> etree.Element:
    """Return a xmlElement for given MaterialIcon.

    Arguments:
        icon: Icon to fetch. If iconname is not explicit (aka does not contain "/"),
              then it will try to get the icon from material/ folder.
    """
    etree.register_namespace("", "http://www.w3.org/2000/svg")
    svg_text = get_icon_svg(icon)
    return etree.fromstring(svg_text)


def write_icon_index():
    import gzip
    import json

    mapping = _get_pyconify_icon_index()
    path = paths.RESOURCES / "icons.json.gzip"
    with gzip.open(path, "w") as file:
        file.write(json.dumps(mapping).encode())


def load_icon_index() -> dict:
    import gzip
    import json

    path = paths.RESOURCES / "icons.json.gzip"
    with gzip.open(path, "r") as file:
        return json.loads(file.read())


if __name__ == "__main__":
    idx = load_icon_index()
    print(idx)
