# myocr.app for Claude

Bank statements often arrive as PDFs, scans or phone photos, and a reconciliation can only be as good as the bank data it starts from. This plugin turns those statements into transactions that are checked against the statement itself: the opening balance, plus the credits, minus the debits, must equal the closing balance printed on the statement, to the cent. When the check passes, no transaction was skipped or misread; when it fails, Claude tells you by how much and where to look.

Claude can read a short statement with selectable text by itself, and checks it the same way. This plugin is for the statements it cannot read reliably: scans, phone photos, long statements with hundreds of transactions, a year of statements at once.

The verified bank side then goes straight into the work you asked for: a bank reconciliation, a month-end close, a cash proof or audit evidence. The plugin is designed to feed reconciliation workflows such as the `reconciliation` skill of the Finance plugin and `close-month` / `month-end-prep` of the Small Business plugin. Without them, Claude prepares a standard bank reconciliation itself.

## Skills

| Skill | What it does |
|---|---|
| `bank-statements` | Bank and card statements (PDF, scan or photo, any bank, any language) → every transaction, the balance check, and a CSV ready for matching against the ledger |
| `verify-balance-report` | Looks up a myocr.app Balance Check Report code (BCR-…) and compares it with the statement or figures you have |
| `document-tables` | Tables from long or scanned documents → Excel, one sheet per table, or the plain text of a scan |

## Get started

1. Install the plugin.
2. Connect the myocr.app connector: in claude.ai or Cowork from the plugin's **Connectors** tab, in Claude Code with `/mcp`. Sign in with your myocr.app account, or create one at the same step; new accounts include free pages to try it.
3. Ask, for example:
   - "Reconcile our current account for September. The bank statement is `statement-2026-09.pdf` and the ledger export is `gl-cash-2026-09.csv`."
   - "Convert these three scanned statements to Excel and tell me whether each one adds up."
   - "A client sent me Balance Check Report BCR-20260914-TESTAA with their statement. Does it match?"

In Claude Code and Cowork, and in chats with code execution, Claude uploads the statement and reads the result by itself when the sandbox can reach `www.myocr.app` (add it to the allowed domains if needed). Otherwise Claude gives you a private upload link, valid for one hour and usable once, and asks you to attach the Excel result.

## What the plugin sends, runs and stores

- **Connector:** `https://www.myocr.app/mcp`, operated by MAD.AI SRL, the company behind myocr.app. You sign in with your myocr.app account (OAuth); the plugin contains no keys or passwords.
- **Files sent:** only the statements and documents you ask Claude to convert, to `www.myocr.app` through the connector, a private upload link (with `curl`) or a direct link you provide. Each conversion uses 1 page of your myocr.app balance per PDF page; failed conversions are refunded.
- **Commands run on your computer or sandbox:** `curl`, to upload a file to its private upload link and to download the result from its private download link on `www.myocr.app`; and `scripts/statement_rows.py`, which reads the downloaded Excel file and writes a CSV next to it, without any network access.
- **Retention:** files are used only for the conversion, are not used to train AI models and are deleted automatically after 30 days. Download links expire after 7 days. Privacy policy: https://www.myocr.app/legal/privacy-policy

The balance check is arithmetic on the extracted data. It does not establish that a statement is authentic, and it is not an audit or a certification.

## Limits

PDF, PNG, JPG and WEBP files. The pages and size allowed per document depend on the account, usually 100 pages and 30 MB; Claude checks them with the connector before a long conversion. Password-protected PDFs must be unlocked first.

## Support

Guide: https://www.myocr.app/docs/mcp. Questions and problems: info@myocr.app.

## License

MIT
