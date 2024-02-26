from typing import Optional

import pandas as pd
from flask import Flask, render_template, request

from pit38.captures import CaptureStdIntoHTML
from pit38.summarizer import Summarizer

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def main() -> str:
    summary: Optional[str] = None
    captured_stdout: Optional[str] = None
    captured_stderr: Optional[str] = None
    if request.method == "POST":
        file_ = request.files["file"] or None
        employment_date = (
            pd.to_datetime(request.form["employment-date"])
            if request.form["employment-date"]
            else None
        )
        if file_:
            with CaptureStdIntoHTML() as captured:
                summary = (
                    Summarizer()
                    .load_schwab_actions(file_)
                    .load_exchange_rates()
                    .summarize_annual()
                    .calculate_remaining()
                    .to_frame(employment_date)
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
    app.run(debug=True)
