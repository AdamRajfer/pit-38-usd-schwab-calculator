from polish_pit_calculator.config import TaxRecord, TaxReport, TaxReporter


class ManualTaxReporter(TaxReporter):
    def generate(self) -> TaxReport:
        year = self.args[0]["year"]
        tax_data = self.args[0]["tax_data"]
        tax_record = TaxRecord(**tax_data)
        tax_report = TaxReport()
        tax_report[year] = tax_record
        return tax_report
