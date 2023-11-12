# pit-38-usd-schwab-calculator

Tool for summarizing taxes for PIT-38 given a Charles Schwab CSV file with full history of USD transactions.

## Installation

```bash
pip install git+https://github.com/AdamRajfer/pit-38-usd-schwab-calculator
```

## Summarization of taxes

1. Go to https://client.schwab.com/app/accounts/transactionhistory/#/.
2. Select the account for which you want to generate the report.
2. Select `All` in `Data Range` field and press `Search`.
3. Press `Export` at the top-right side of the page in order to download the csv file.
4. After downloading the file, run the following command in order to get the tax summarization:

```bash
pit_38_usd_schwab_calculator <path_to_the_exported_csv_file>
```

By default, it will generate the report for the preceeding year. If you want to specify the exact year, use `--year` flag (eg. `--year 2022`).
