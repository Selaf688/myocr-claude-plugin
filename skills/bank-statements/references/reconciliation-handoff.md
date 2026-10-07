# Using the verified bank side

Read this when the user's request continues after the conversion: a bank reconciliation, a month-end close, a cash proof or audit evidence. If a reconciliation or close workflow is already loaded (for example the finance plugin's `reconciliation` skill or the small-business `month-end-prep`), follow that workflow and use this file only for the bank side.

## The CSV from `scripts/statement_rows.py`

| Column | Meaning |
|---|---|
| `statement` | 1, 2… when one file holds several statements |
| `row` | Row number in the Excel `transactions` sheet, to point the user back to the source |
| `date` | Date as printed on the statement |
| `date_iso` | `YYYY-MM-DD` when the date format is unambiguous, otherwise empty |
| `description` | As printed |
| `credit`, `debit` | Money in and money out, positive numbers |
| `amount` | `credit - debit`: positive = money in, negative = money out |
| `balance` | Running balance as printed, with its sign (overdrawn = negative), when the statement shows it |

Numbers use a dot as the decimal separator and no thousands separator. When `date_iso` is empty, the dates are ambiguous (for example 03/04): check the statement's own format (day first or month first) with the user before matching by date.

## Bank reconciliation

The bank's closing balance is the "balance per bank statement". Match the statement's transactions with the general ledger cash account for the same period:

1. Match on amount and direction first: a bank credit matches a debit to cash in the ledger, and the other way round.
2. Then on date: the ledger date can precede the bank date by a few days (cheques, transfers, card settlements). Use ±5 days unless the user gives a rule.
3. Then on description or reference, when several candidates remain.
4. One bank line can settle several ledger lines (a deposit of several receipts, a batch payment), and the other way round. Match those groups only when the amounts add up exactly.
5. Never force a match to make the difference zero.

Then sort what is left:

- In the ledger, not on the statement: deposits in transit and outstanding payments (timing differences).
- On the statement, not in the ledger: bank fees, interest, direct debits, transfers not yet recorded. Each needs an adjusting entry.
- Neither: errors to investigate.

Standard format:

```
Balance per bank statement (verified closing balance)   X
Add: deposits in transit                                 X
Less: outstanding payments                              (X)
Add/less: bank errors                                    X
Adjusted bank balance                                    X

Balance per general ledger                               X
Add: credits on the statement not yet recorded           X
Less: charges on the statement not yet recorded         (X)
Add/less: ledger errors                                  X
Adjusted ledger balance                                  X

Difference                                            0.00
```

State the period and the currency. List every reconciling item with its date, description, amount and category. If the balance check was not consistent, put that first: the bank side is unchecked, and part of the difference may come from the extraction.

## Month-end close and cash proof

Report the closing balance per bank, the statement end date, the number of transactions and the balance check result for each account. When a statement ends before the close date, say which days are not covered.

## Audit evidence

A short record the user can paste into a workpaper:

```
Bank statement: <bank>, account ending <last 4>, <currency>, <period>
Opening balance <X>; credits <Y> (<n> items); debits <Z> (<m> items); closing balance per statement <W>
Balance check: <consistent | inconsistent, difference D | not available>
Source: myocr.app conversion <job_id>, <date>
Note: arithmetic check on the extracted data; it does not establish that the document is authentic.
```

If the user also has a myocr.app Balance Check Report code (BCR-…), the `verify-balance-report` skill checks it against the public record.
