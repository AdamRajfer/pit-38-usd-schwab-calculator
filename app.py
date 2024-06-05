from typing import Optional

import pandas as pd
from flask import Flask, render_template, request

from pit38.captures import CaptureStdIntoHTML
from pit38.schwab import (
    format_summary,
    load_current_stock_values,
    load_exchange_rates,
    load_schwab_actions,
    load_summary,
)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def main() -> str:
    formatted_summary: Optional[str] = None
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
                schwab_actions = load_schwab_actions(file_)
                symbols = sorted(
                    set(
                        action.Symbol
                        for action in schwab_actions
                        if isinstance(action.Symbol, str)
                    )
                )
                current_stock_values = load_current_stock_values(symbols)
                min_year = min(action.Date.year for action in schwab_actions)
                exchange_rates = load_exchange_rates(min_year)
                summary = load_summary(
                    schwab_actions=schwab_actions,
                    current_stock_values=current_stock_values,
                    exchange_rates=exchange_rates,
                )
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
