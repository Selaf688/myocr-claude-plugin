---
name: verify-balance-report
description: >-
  Checks a myocr.app Balance Check Report from its code (BCR-YYYYMMDD-XXXXXX), for example one that a
  client, borrower or colleague sent together with a bank statement, and summarises the public record:
  bank, period, last 4 digits of the account, opening and closing balances, totals, number of
  transactions and whether the extracted transactions add up to the printed closing balance. Use it for
  audit support, lending reviews or bookkeeping reviews whenever someone quotes a BCR code or asks
  whether such a report is genuine.
argument-hint: "<BCR-YYYYMMDD-XXXXXX>"
---

# Verify a Balance Check Report

A Balance Check Report is a one-page PDF that a myocr.app user can download after converting a bank statement on the website. myocr.app keeps a public record of it, and the code on the PDF lets anyone look that record up, without an account.

1. Call `verify_balance_report` with the code exactly as written (format `BCR-YYYYMMDD-XXXXXX`). If the tool says the code is not valid or does not exist, ask the user to check it for typos (letters O and I, digits 0 and 1).
2. Summarise the record: bank, period, account ending, currency, opening balance, credits, debits, printed closing balance, difference, number of transactions, the result and the date of the report. Give the public page (`verify_url`), so the user can keep it with their working papers.
3. If the user also has the statement or the client's figures, compare them with the record: same bank, same last 4 digits, same period, same opening and closing balances, same number of transactions. Report each match or difference. A difference means the report does not belong to that statement, or one of the two was changed.
4. Explain the limit in one sentence: the report shows that the transactions extracted from a statement add up to its printed closing balance. It does not show that the statement is authentic, and it is not an audit opinion.

The record never contains the account holder's name or the full account number. Don't try to obtain them through the tool.
