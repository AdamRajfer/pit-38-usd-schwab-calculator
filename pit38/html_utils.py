import sys
from contextlib import AbstractContextManager
from io import StringIO
from typing import Any

from ansi2html import Ansi2HTMLConverter


class CaptureStdIntoHTML(AbstractContextManager):
    def __enter__(self) -> "CaptureStdIntoHTML":
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.stdout_content = sys.stdout.getvalue()  # type: ignore
        self.stderr_content = sys.stderr.getvalue()  # type: ignore
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    @property
    def html_stdout_content(self) -> str:
        return self._get_html_content(self.stdout_content)

    @property
    def html_stderr_content(self) -> str:
        return self._get_html_content(self.stderr_content)

    def _get_html_content(self, content: str) -> str:
        return Ansi2HTMLConverter().convert(content, full=False)
