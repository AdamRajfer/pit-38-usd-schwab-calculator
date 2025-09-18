# Polish PIT Calculator

Tool for generating content for Polish PIT forms.

## 1. Installation

```bash
poetry install
```

## 2. Usage

### 2.1. Charles Schwab Employee Sponsored

1. Go to https://client.schwab.com/app/accounts/transactionhistory/#/.
2. Select the Employee Sponsored account for which you want to generate the report.
3. Select "Previous 4 Years" in Data Range field and press Search.
4. Press Export at the top-right side of the page in order to download the CSV file.
5. Run:

```python
from pathlib import Path
from polish_pit_calculator.schwab import SchwabEmployeeSponsoredTaxReporter

report_path = Path("PATH_TO_YOUR_REPORT.csv")
tax_reporter = SchwabEmployeeSponsoredTaxReporter(report_path)
tax_report = tax_reporter.generate()
print(tax_report.to_string())
```

It will generate the following report (filled with the calculated content):

```bash
|                                                                 |   2022 |   2023 |   2024 |   2025 |
|-----------------------------------------------------------------|--------|--------|--------|--------|
| Trade Revenue (PIT-38/C20)                                      |   0.00 |   0.00 |   0.00 |   0.00 |
| Trade Cost (PIT-38/C21)                                         |   0.00 |   0.00 |   0.00 |   0.00 |
| Trade Loss from Previous Years (PIT-38/D28)                     |   0.00 |   0.00 |   0.00 |   0.00 |
| Trade Loss (PIT-38/D28 - Next Year)                             |   0.00 |   0.00 |   0.00 |   0.00 |
| Crypto Revenue (PIT-38/E34)                                     |   0.00 |   0.00 |   0.00 |   0.00 |
| Crypto Cost (PIT-38/E35)                                        |   0.00 |   0.00 |   0.00 |   0.00 |
| Crypto Cost Excess from Previous Years (PIT-38/E36)             |   0.00 |   0.00 |   0.00 |   0.00 |
| Crypto Cost Excess (PIT-38/E36 - Next Year)                     |   0.00 |   0.00 |   0.00 |   0.00 |
| Domestic Interest Tax (PIT-38/G44)                              |   0.00 |   0.00 |   0.00 |   0.00 |
| Foreign Interest Tax (PIT-38/G45)                               |   0.22 |   0.00 |   0.00 |   0.00 |
| Foreign Interest Withholding Tax (PIT-38/G46)                   |   0.19 |   0.00 |   0.00 |   0.00 |
| Employment Profit Deduction (PIT/O/B11 -> PIT-37/F124)          |   0.00 |   0.00 |   0.00 |   0.00 |
| Total Profit (DSF-1/C18 - If Solidarity Tax > 0.00)             |   0.00 |   0.00 |   0.00 |   0.00 |
| Total Profit Deductions (DSF-1/CC19 - If Solidarity Tax > 0.00) |   0.00 |   0.00 |   0.00 |   0.00 |
| Solidarity Tax                                                  |   0.00 |   0.00 |   0.00 |   0.00 |
| Total Tax                                                       |   0.03 |   0.00 |   0.00 |   0.00 |
```
