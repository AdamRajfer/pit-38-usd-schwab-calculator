from typing import Optional

from flask import Flask, render_template, request

from pit38.html_utils import CaptureStdIntoHTML
from pit38.schwab import Schwab

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def main() -> str:
    summary: Optional[str] = None
    captured_stdout: Optional[str] = None
    captured_stderr: Optional[str] = None
    if request.method == "POST":
        file_ = request.files["file"] or None
        employment_date = request.form["employment-date"] or None
        if file_:
            with CaptureStdIntoHTML() as captured:
                summary = (
                    Schwab(file_, employment_date)
                    .summarize()
                    .style.format("{:,.2f}")
                    .set_table_styles(
                        [
                            {
                                "selector": "th, td",
                                "props": [("text-align", "right")],
                            }
                        ],
                        overwrite=False,
                    )
                    .to_html()
                )
            captured_stdout = captured.html_stdout_content
            captured_stderr = captured.html_stderr_content
    return render_template(
        "app.html",
        summary=summary,
        captured_stdout=captured_stdout,
        captured_stderr=captured_stderr,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
