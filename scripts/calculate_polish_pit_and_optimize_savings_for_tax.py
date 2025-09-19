from jsonargparse import CLI

from polish_pit_calculator.config import TaxReport, TaxReporter
from polish_pit_calculator.optimizer import SavingsForTaxOptimizer


def main(
    tax_reporters: list[TaxReporter], *, savings: float, interest_rate: float
) -> None:
    tax_report = TaxReport()
    for tax_reporter in tax_reporters:
        tax_report += tax_reporter.generate()
    optimizer = SavingsForTaxOptimizer().fit(
        tax_report, savings, interest_rate
    )
    print(f"{tax_report.to_string()}\n{optimizer.msg_}")


if __name__ == "__main__":
    CLI(main)
