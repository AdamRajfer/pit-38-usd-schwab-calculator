import pandas as pd
from flask import Flask, render_template, request

from pit38.captures import CaptureStdIntoHTML
from pit38.schwab import (
    format_summary,
    load_schwab_actions,
    summarize_schwab_actions,
)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def main() -> str:
    formatted_summary: str | None = None
    captured_stdout: str | None = None
    captured_stderr: str | None = None
    if request.method == "POST":
        file_ = request.files["file"] or None
        employment_date = (
            pd.to_datetime(request.form["employment-date"])
            if request.form["employment-date"]
            else None
        )
        if file_:
            with CaptureStdIntoHTML() as captured:
                schwab_actions = load_schwab_actions(file_)
                summary = summarize_schwab_actions(schwab_actions)
                formatted_summary = format_summary(
                    summary=summary,
                    employment_date=employment_date,
                )
            captured_stdout = captured.html_stdout_content
            captured_stderr = captured.html_stderr_content
    return render_template(
        "app.html",
        summary=formatted_summary,
        captured_stdout=captured_stdout,
        captured_stderr=captured_stderr,
    )


if __name__ == "__main__":
    app.run(debug=True)
