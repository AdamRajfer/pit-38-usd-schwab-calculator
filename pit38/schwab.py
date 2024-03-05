from collections import defaultdict
from datetime import datetime
from typing import Dict, Hashable, List, Optional

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
        for share in SchwabActionsFromFile(self.path).load().exchange():
            if share.Action == "Deposit":
                for _ in range(int(share.Quantity)):
                    self.append(share)
                share.buy_msg()
            elif share.Action == "Sale":
                sold_shares: List[SchwabAction] = []
                for _ in range(int(share.Shares)):
                    sold_shares.append(self.pop(0))
                    self.summary[share.Date.year] += IncomeSummary(
                        income=share.sale_price,
                        cost=sold_shares[-1].purchase_price,
                    )
                share.sell_msg(sold_shares)
                del sold_shares
            elif share.Action == "Lapse":
                share.lapse_msg()
            elif share.Action in [
                "Wire Transfer",
                "Tax Withholding",
                "Dividend",
            ]:
                share.amount_msg()
            else:
                share.error_msg()
        self.summary["remaining"] = IncomeSummary()
        for share in self:
            self.summary["remaining"] += IncomeSummary(
                income=share.current_sale_price,
                cost=share.purchase_price,
            )
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
