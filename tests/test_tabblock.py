from __future__ import annotations

import mknodes


EXPECTED = """/// tab | Tab1
Some text
///

/// tab | Tab2
Another text
///

"""


def test_tabblock():
    tabs = dict(Tab1="Some text", Tab2="Another text")
    tabblock = mknodes.TabBlock(tabs)
    assert str(tabblock) == EXPECTED
