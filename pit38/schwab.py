import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, Hashable, Optional

import pandas as pd

from pit38.income import IncomeSummary
from pit38.preprocessing import SchwabActionsFromFile
from pit38.stock import SchwabAction


class SchwabActions(list[SchwabAction]):
    def __init__(
        self, path: str, employment_date: Optional[datetime] = None
    ) -> None:
        self.path = path
        self.employment_date = employment_date
        self.summary: Dict[Hashable, IncomeSummary] = defaultdict(
            IncomeSummary
        )

    def prepare_summary(self) -> "SchwabActions":
        for action in SchwabActionsFromFile(self.path).load().exchange():
            name = action.Action
            desc = action.Description
            date = action.Date
            error = False
            if name == "Deposit":
                msg = self._buy(action)
            elif name == "Sale":
                msg = self._sell(action)
            elif name == "Lapse":
                msg = f"{int(action.Quantity)} shares."
            elif name in ["Wire Transfer", "Tax Withholding", "Dividend"]:
                msg = f"{action.Amount:.2f} USD."
            else:
                msg = f"Unknown action! The summary may not be adequate."
                error = True
            msg = f"[{date.strftime('%Y-%m-%d')}] {name} ({desc}): {msg}"
            print(msg)
            if error:
                print(msg, file=sys.stderr)
        self.summary["remaining"] = self.remaining
        return self

    def to_html(self) -> str:
        df = pd.DataFrame({k: v.__dict__ for k, v in self.summary.items()})
        df = df.assign(total=df.sum(axis=1))
        if self.employment_date is not None:
            months = (datetime.now() - self.employment_date).days / 30.4375
            df["total/month"] = df["total"] / months
        return (
            df.style.format("{:,.2f}")
            .set_table_styles(
                [{"selector": "th, td", "props": [("text-align", "right")]}],
                overwrite=False,
            )
            .to_html()
        )

    def _buy(self, shares: SchwabAction) -> str:
        quantity = int(shares.Quantity)
        for _ in range(quantity):
            self.append(shares)
        return f"{quantity} ESPP shares for {shares.purchase_price * quantity:.2f} PLN."

    def _sell(self, shares: SchwabAction) -> str:
        msg = ""
        for _ in range(int(shares.Shares)):
            share = self.pop(0)
            self.summary[shares.Date.year] += IncomeSummary(
                shares.sale_price, share.purchase_price
            )
            msg += f"\n  -> 1 {share.Description} share for {shares.sale_price:.2f} PLN bought for {share.purchase_price:.2f} PLN."
        return msg

    @property
    def remaining(self) -> IncomeSummary:
        remaining = IncomeSummary()
        for share in self:
            remaining += IncomeSummary(
                share.current_sale_price, share.purchase_price
            )
        return remaining
