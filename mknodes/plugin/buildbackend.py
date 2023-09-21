from __future__ import annotations

from mknodes.utils import log, requirements


logger = log.get_logger(__name__)


class BuildBackend:
    def collect(self, files: dict[str, str | bytes], reqs: requirements.Requirements):
        self.collect_extensions(reqs.markdown_extensions)
        self.collect_js_links(reqs.js_links)
        self.collect_js_files(reqs.js_files)
        self.collect_css(reqs.css)
        self.collect_templates(reqs.templates)
        self.collect_files(files)

    def collect_files(self, files):
        pass

    def collect_js_links(self, js_links):
        pass

    def collect_js_files(self, js_files):
        pass

    def collect_css(self, css):
        pass

    # def collect_css_links(self, css):
    #     pass

    def collect_extensions(self, extensions):
        pass

    def collect_templates(self, templates):
        pass


if __name__ == "__main__":
    b = BuildBackend()
