# Connector errors and what to do

The myocr.app tools explain each failure in their reply. Pass the meaning on in plain words and suggest the next step. When a conversion is not started, nothing is charged; when it fails, the pages are refunded.

| What the tool says | What to tell the user |
|---|---|
| Not enough pages | The document has more pages than the account has left. More pages can be added on myocr.app; the tool reply links the page with plans and packs. |
| Too many pages for one document | Split the PDF into parts within the limit and convert them one by one. Keep each part a whole set of pages, in order. |
| File larger than the size limit | Compress or split the PDF, or export it again from online banking. |
| Protected by a password | Remove the password (open the PDF and save or print it again without protection), then upload it again. |
| Not a PDF, PNG, JPG or WEBP | Convert the file to PDF, or download the statement again as PDF from online banking. A link to a sharing page (Google Drive, Dropbox) is not a direct link: use the upload link instead. |
| File could not be read | The file may be damaged: try another copy. |
| Same file failed several times | Use a clearer copy: the original PDF from online banking, or a scan made with a phone scanner app. |
| 3 conversions already running | Wait for one to finish, then start the next. |
| Monthly limit for bank statements reached | The plan's limit for bank statement extraction is used up this month. |
| Upload link already used / expired | Check the conversion that link started, or create a new link. |
| Account not available | Reconnect the myocr.app connector and sign in again. |
| myocr.app could not start the conversion | Temporary problem: try again in a minute. |

When the conversion is done but `result_expired` is true, the result was older than the retention period and must be converted again.

A photo of each page works, but a complete PDF downloaded from online banking gives the best result and lets the balance check cover the whole period.
