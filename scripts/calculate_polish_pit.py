from jsonargparse import CLI

from polish_pit_calculator.config import TaxReport, TaxSummaryConfig


def main(cfg: TaxSummaryConfig) -> None:
    tax_report = TaxReport()
    for tax_reporter in cfg.tax_reporters:
        tax_report += tax_reporter.generate()
    print(tax_report.to_string())


if __name__ == "__main__":
    CLI(main)
