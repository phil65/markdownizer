from __future__ import annotations

import logging

from mknodes.basenodes import mkbasetable


logger = logging.getLogger(__name__)


class MkTable(mkbasetable.MkBaseTable):
    """Class representing a formatted table."""

    def _to_markdown(self) -> str:
        if not any(self.data[k] for k in self.data):
            return ""
        formatters = [f"{{:<{self.width_for_column(c)}}}" for c in self.data]
        headers = [formatters[i].format(k) for i, k in enumerate(self.data.keys())]
        divider = [self.width_for_column(c) * "-" for c in self.data]
        data = [
            [
                formatters[i].format(str(k).replace("\n", "<br>"))
                for i, k in enumerate(row)
            ]
            for row in self.iter_rows()
        ]
        header_txt = "| " + " | ".join(headers) + " |"
        divider_text = "| " + " | ".join(divider) + " |"
        data_txt = ["| " + " | ".join(line) + " |" for line in data]
        return "\n".join([header_txt, divider_text, *data_txt]) + "\n"

    @staticmethod
    def create_example_page(page):
        import mknodes

        node_1 = MkTable(data={"Column A": ["A", "B", "C"], "Column B": ["C", "D", "E"]})
        # data can be given in different shapes.
        page += mknodes.MkReprRawRendered(node_1)
        dicts = [{"col 1": "abc", "col 2": "cde"}, {"col 1": "fgh", "col 2": "ijk"}]
        node_2 = MkTable(data=dicts)
        page += mknodes.MkReprRawRendered(node_2)


if __name__ == "__main__":
    table = MkTable(data={"Column A": ["A", "B", "C"], "Column B": ["C", "D", "E"]})
    print(table)
