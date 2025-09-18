from jsonargparse import CLI

from polish_pit_calculator.config import TaxReport, TaxSummaryConfig
from polish_pit_calculator.optimizer import SavingsForTaxOptimizer


def main(cfg: TaxSummaryConfig) -> None:
    tax_report = TaxReport()
    for tax_reporter in cfg.tax_reporters:
        tax_report += tax_reporter.generate()
    optimizer = SavingsForTaxOptimizer().fit(tax_report, cfg.savings)
    print(f"{tax_report.to_string()}\n{optimizer.msg_}")


if __name__ == "__main__":
    CLI(main)
