# pit-38-usd-schwab-calculator

Tool for summarizing taxes for PIT-38 given a Charles Schwab CSV file with full history of USD transactions.

## Setup

```bash
git clone https://github.com/AdamRajfer/pit-38-usd-schwab-calculator
cd pit-38-usd-schwab-calculator
pip install -r requirements.txt
```

## Summary

1. Go to https://client.schwab.com/app/accounts/transactionhistory/#/.
2. Select the account for which you want to generate the report.
3. Select `Previous 4 Years` in `Data Range` field and press `Search`.
4. Press `Export` at the top-right side of the page in order to download the csv file.
5. Run the app.

```bash
python app.py
```
