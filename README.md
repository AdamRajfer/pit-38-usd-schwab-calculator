# pit-38-usd-schwab-calculator

Tool for summarizing taxes for PIT-38 given a Charles Schwab CSV file with full history of USD transactions.

## Installation

```bash
pip install git+https://github.com/AdamRajfer/pit-38-usd-schwab-calculator
```

## Summarization of taxes

1. Create your own configuration file and place it in `conf/` directory. Here is an example:

```yaml
path: ~/EquityAwardsCenter_Transactions_20240217211552.csv
employment_date: 2020-01-01
salary_gross_per_month: 10000.00
salary_net_per_month: 7500.00
```

2. Go to https://client.schwab.com/app/accounts/transactionhistory/#/.
3. Select the account for which you want to generate the report.
4. Select `All` in `Data Range` field and press `Search`.
5. Press `Export` at the top-right side of the page in order to download the csv file.
6. After downloading the file, run the following command in order to get the tax summarization:

```bash
python summarize.py --config-name <path_to_your_config_yaml_file>
```
