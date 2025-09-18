from dataclasses import dataclass

from polish_pit_calculator.config import TaxRecord, TaxReport, TaxReporter


@dataclass(frozen=True)
class RawTaxReporter(TaxReporter):
    tax_report_data: dict[int, dict[str, float]]

    def generate(self) -> TaxReport:
        tax_report = TaxReport()
        for year, tax_record_data in self.tax_report_data.items():
            tax_report[year] = TaxRecord(**tax_record_data)
        return tax_report
