#!/usr/bin/env python3
"""Read a myocr.app bank statement workbook (.xlsx) and write its transactions as CSV.

Usage:
    python3 statement_rows.py statement.xlsx [--csv out.csv]

Prints a JSON summary per statement (balances, totals, number of transactions and the
balance check recomputed from the file) and writes one CSV row per transaction with the
columns: statement, row, date, date_iso, description, credit, debit, amount, balance.
Lines without an amount (opening balance, carried forward) are left out unless --all-rows.

Standard library only (Python 3.8+). Reads the local file and writes the CSV; it makes no
network calls.
"""
import argparse
import csv
import json
import os
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

NS_MAIN = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
NS_REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
NS_PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'
MAX_MEMBER_BYTES = 50 * 1024 * 1024
TOLERANCE = 0.01


# ------------------------------------------------------------------ reading the .xlsx

def _read_member(zf, name):
    info = zf.getinfo(name)
    if info.file_size > MAX_MEMBER_BYTES:
        raise ValueError(f'{name} is too large to read')
    return zf.read(name)


def _col_index(ref):
    letters = re.match(r'[A-Z]+', ref or 'A').group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_workbook(path):
    """{sheet name: [[cell values], ...]} with strings and numbers as stored; list index = Excel row - 1."""
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        shared = []
        if 'xl/sharedStrings.xml' in names:
            root = ET.fromstring(_read_member(zf, 'xl/sharedStrings.xml'))
            for si in root.iter(NS_MAIN + 'si'):
                shared.append(''.join(t.text or '' for t in si.iter(NS_MAIN + 't')))
        rels = {}
        rel_root = ET.fromstring(_read_member(zf, 'xl/_rels/workbook.xml.rels'))
        for rel in rel_root.iter(NS_PKG + 'Relationship'):
            target = rel.get('Target') or ''
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            rels[rel.get('Id')] = os.path.normpath(target).replace(os.sep, '/')
        wb_root = ET.fromstring(_read_member(zf, 'xl/workbook.xml'))
        sheets = {}
        for sh in wb_root.iter(NS_MAIN + 'sheet'):
            target = rels.get(sh.get(NS_REL + 'id'))
            if not target or target not in names:
                continue
            root = ET.fromstring(_read_member(zf, target))
            rows = []
            for row in root.iter(NS_MAIN + 'row'):
                cells = {}
                for c in row.iter(NS_MAIN + 'c'):
                    kind = c.get('t')
                    v = c.find(NS_MAIN + 'v')
                    if kind == 's' and v is not None:
                        value = shared[int(v.text)]
                    elif kind == 'inlineStr':
                        value = ''.join(t.text or '' for t in c.iter(NS_MAIN + 't'))
                    elif v is None or v.text is None:
                        value = ''
                    elif kind in ('str', 'e'):
                        value = v.text
                    elif kind == 'b':
                        value = v.text == '1'
                    else:
                        try:
                            value = float(v.text)
                        except ValueError:
                            value = v.text
                    cells[_col_index(c.get('r'))] = value
                number = int(row.get('r') or len(rows) + 1)
                while len(rows) < number - 1:
                    rows.append([])
                rows.append([cells.get(i, '') for i in range(max(cells) + 1)] if cells else [])
            sheets[sh.get('name')] = rows
    return sheets


# ------------------------------------------------------------------ amounts (same rules as myocr.app)

_NEG_SUFFIX = re.compile(r'(?<=[\d\s)])\(?\s*(O/?D|DR|DB|D)\.?\s*\)?\s*$', re.I)
_POS_SUFFIX = re.compile(r'(?<=[\d\s)])\(?\s*(CR|C)\.?\s*\)?\s*$', re.I)
_CARRY_FORWARD = re.compile(r'CARRIED\s+F(?:OR)?WA?R?D|\bC\s*/\s*F\b|A\s+RIPORTARE|[ÜU]E?BERTRAG|A\s+REPORTER|'
                            r'SUMA\s+Y\s+SIGUE|A\s+TRANSPORTAR|SALDO\s+A\s+TRANSPORTAR', re.I)


def _text(v):
    """Cell value as text, without the apostrophe that guards formula-like cells."""
    if v is None or v == '':
        return ''
    if isinstance(v, float):
        return repr(v)
    s = str(v).strip()
    return s[1:] if s.startswith("'") else s


def parse_amount(value, style=None):
    if isinstance(value, float):
        return value
    t = _text(value)
    if not t:
        return None
    neg = t.startswith('(') and t.endswith(')')
    t = re.sub(r'[^0-9.,\-]', '', t)
    if not t or t in ('-', '.', ','):
        return None
    if style == 'comma':
        t = t.replace('.', '').replace(',', '.')
    elif style == 'dot':
        t = t.replace(',', '')
    elif ',' in t and '.' in t:
        t = t.replace('.', '').replace(',', '.') if t.rfind(',') > t.rfind('.') else t.replace(',', '')
    elif ',' in t:
        t = t.replace(',', '.') if len(t.rsplit(',', 1)[-1]) == 2 else t.replace(',', '')
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def parse_balance(value, style=None):
    """Like parse_amount, plus overdraft suffixes (D, DR, OD, O/D, DB) and a trailing minus."""
    if isinstance(value, float):
        return value
    t = _text(value)
    if not t:
        return None
    neg = False
    m = _NEG_SUFFIX.search(t)
    if m:
        neg, t = True, t[:m.start()].strip()
    else:
        m = _POS_SUFFIX.search(t)
        if m:
            t = t[:m.start()].strip()
    if t.endswith('-') and not t.startswith('-'):
        neg, t = True, t[:-1].strip()
    v = parse_amount(t, style)
    if v is None:
        return None
    return -abs(v) if neg else v


def infer_decimal_style(values):
    comma = dot = 0
    for v in values:
        if isinstance(v, float):
            continue
        t = re.sub(r'[^0-9.,]', '', _text(v))
        if re.search(r',\d{2}$', t):
            comma += 1
        elif re.search(r'\.\d{2}$', t):
            dot += 1
    if comma > dot:
        return 'comma'
    if dot > comma:
        return 'dot'
    return None


# ------------------------------------------------------------------ dates

_MONTHS = {m: i for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], start=1)}
_MONTHS.update({'sept': 9, 'gen': 1, 'mag': 5, 'giu': 6, 'lug': 7, 'ago': 8, 'set': 9, 'ott': 10, 'dic': 12,
                'ene': 1, 'abr': 4, 'dez': 12, 'mär': 3, 'mai': 5, 'okt': 10, 'fev': 2, 'out': 10})
_NUMERIC_DATE = re.compile(r'^\s*(\d{1,4})[./\-](\d{1,2})(?:[./\-](\d{2,4}))?\s*$')
_NAMED_DATE = re.compile(r'^\s*(\d{1,2})[\s\-.]*([A-Za-zÀ-ÿ]{3,9})\.?[\s\-,.]*(\d{2,4})?\s*$')
_NAMED_DATE_US = re.compile(r'^\s*([A-Za-zÀ-ÿ]{3,9})\.?\s+(\d{1,2}),?\s*(\d{2,4})?\s*$')


def _year(y, default_year):
    if not y:
        return default_year
    y = int(y)
    return y + 2000 if y < 100 else y


def date_order(dates):
    """'day_first', 'month_first' or None, from the numeric dates that are not ambiguous."""
    day_first = month_first = 0
    for d in dates:
        m = _NUMERIC_DATE.match(d or '')
        if not m or len(m.group(1)) == 4:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12 >= b:
            day_first += 1
        elif b > 12 >= a:
            month_first += 1
    if day_first and not month_first:
        return 'day_first'
    if month_first and not day_first:
        return 'month_first'
    return None


def to_iso(d, order, default_year):
    d = (d or '').strip()
    m = _NUMERIC_DATE.match(d)
    try:
        if m:
            if len(m.group(1)) == 4:
                y, mo, day = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
            elif order == 'day_first':
                day, mo, y = int(m.group(1)), int(m.group(2)), _year(m.group(3), default_year)
            elif order == 'month_first':
                mo, day, y = int(m.group(1)), int(m.group(2)), _year(m.group(3), default_year)
            else:
                return ''
        else:
            m = _NAMED_DATE.match(d)
            if m:
                day, mon, y = int(m.group(1)), m.group(2), _year(m.group(3), default_year)
            else:
                m = _NAMED_DATE_US.match(d)
                if not m:
                    return ''
                mon, day, y = m.group(1), int(m.group(2)), _year(m.group(3), default_year)
            mo = _MONTHS.get(mon.lower()[:4]) or _MONTHS.get(mon.lower()[:3])
            if not mo:
                return ''
        if not y or not (1 <= mo <= 12 and 1 <= day <= 31):
            return ''
        return f'{y:04d}-{mo:02d}-{day:02d}'
    except (TypeError, ValueError):
        return ''


# ------------------------------------------------------------------ statements

def _label_map(rows):
    out = {}
    for r in rows:
        if len(r) >= 2 and _text(r[0]):
            out[_text(r[0]).lower()] = r[1]
    return out


def _last4(account):
    digits = re.sub(r'\D', '', _text(account))
    return digits[-4:] if digits else ''


def _r2(v):
    return None if v is None else round(v, 2) + 0.0      # + 0.0: no "-0.0" in the output


def statement_numbers(sheets, all_rows=False):
    """Every statement in the workbook: summary + transaction rows (only rows with an amount, unless all_rows)."""
    indexes = sorted({int(m.group(1)) for name in sheets
                      for m in [re.match(r'transactions (\d+)$', name or '')] if m})
    result = []
    for i in indexes:
        head = _label_map(sheets.get(f'header {i}', []))
        tx_rows = sheets.get(f'transactions {i}', [])
        check = _label_map(sheets.get(f'balance check {i}', []))
        # (Excel row number, first five cells) of every non-empty row below the column headings
        cells = [(n, (r + [''] * 5)[:5]) for n, r in enumerate(tx_rows[1:], start=2) if any(_text(c) for c in r)]
        style = infer_decimal_style([head.get('beginning balance'), head.get('ending balance')] +
                                    [v for _n, c in cells for v in (c[2], c[3], c[4])])
        opening = parse_balance(head.get('beginning balance'), style)
        closing = parse_balance(head.get('ending balance'), style)
        dates = [_text(c[0]) for _n, c in cells]
        order = date_order(dates)
        years = re.findall(r'(?:19|20)\d{2}', _text(head.get('statement period')))
        default_year = int(years[-1]) if years else None
        rows, credits, debits, n_moves, n_signed = [], 0.0, 0.0, 0, 0
        last_balance, last_desc = None, ''
        for n, c in cells:
            credit = parse_amount(c[2], style) or 0.0
            debit = parse_amount(c[3], style) or 0.0
            balance = parse_balance(c[4], style)
            # the check adds the columns as myocr.app does; the CSV reads the columns by meaning
            # (Deposit = money in, Withdrawal = money out) whatever sign is printed
            credits += credit
            debits += debit
            if credit or debit:
                n_moves += 1
            if credit < 0 or debit < 0:
                n_signed += 1
            if balance is not None:
                last_balance, last_desc = balance, _text(c[1])
            if not (credit or debit or all_rows):
                continue        # "Opening balance", "carried forward" and other lines without an amount
            rows.append({'statement': i, 'row': n, 'date': _text(c[0]), 'date_iso': to_iso(_text(c[0]), order, default_year),
                         'description': str(c[1] if c[1] is not None else ''), 'credit': _r2(abs(credit)),
                         'debit': _r2(abs(debit)), 'amount': _r2(abs(credit) - abs(debit)), 'balance': _r2(balance)})
        summary = {
            'statement': i,
            'bank': _text(head.get('bank name')),
            'account_last4': _last4(head.get('account number')),
            'period': _text(head.get('statement period')),
            'currency': _text(head.get('currency')),
            'opening_balance': _r2(opening),
            'closing_balance': _r2(closing),
            'credits_total': _r2(credits),
            'debits_total': _r2(debits),
            'transactions': n_moves,
            'date_order': order or ('iso' if dates and all(re.match(r'\d{4}-', d) for d in dates if d) else 'unknown'),
        }
        if n_signed:
            summary['rows_with_a_minus_sign_in_deposit_or_withdrawal'] = n_signed
        if opening is None or closing is None or not cells:
            summary.update({'computed_closing_balance': None, 'difference': None, 'check': 'not_available'})
        else:
            computed = opening + credits - debits
            delta = computed - closing
            ok = abs(delta) <= TOLERANCE
            summary.update({'computed_closing_balance': _r2(computed), 'difference': _r2(delta),
                            'check': 'consistent' if ok else 'inconsistent'})
            # The transactions add up to the last running balance, but the printed closing balance is a
            # different figure: typical of one page of a longer statement. Only a "carried forward" last
            # row (or myocr.app's own verdict below) makes it more than a hint.
            if not ok and last_balance is not None and abs(computed - last_balance) <= TOLERANCE \
                    and abs(closing - last_balance) > TOLERANCE:
                summary['transactions_add_up_to_last_running_balance'] = True
                if _CARRY_FORWARD.search(last_desc):
                    summary['incomplete_statement'] = True
        verdict = _text(check.get('result'))
        if verdict:
            summary['myocr_result'] = verdict
            if verdict.upper().startswith('INCOMPLETE'):
                summary['incomplete_statement'] = True
        result.append((summary, rows))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description='myocr.app bank statement workbook to CSV, with the balance check.')
    ap.add_argument('xlsx', help='the .xlsx file downloaded from myocr.app')
    ap.add_argument('--csv', help='where to write the transactions (default: next to the .xlsx)')
    ap.add_argument('--all-rows', action='store_true',
                    help='also write the lines without an amount (opening balance, carried forward...)')
    args = ap.parse_args(argv)
    try:
        sheets = read_workbook(args.xlsx)
    except (OSError, zipfile.BadZipFile, KeyError, ValueError, ET.ParseError) as e:
        print(json.dumps({'error': f'Could not read {args.xlsx} as an Excel workbook: {e}'}))
        return 2
    statements = statement_numbers(sheets, args.all_rows)
    if not statements:
        print(json.dumps({'error': 'No "transactions" sheet found: this is not a myocr.app bank statement workbook.',
                          'sheets': sorted(sheets)}))
        return 2
    out = args.csv or os.path.splitext(args.xlsx)[0] + '.csv'
    cols = ['statement', 'row', 'date', 'date_iso', 'description', 'credit', 'debit', 'amount', 'balance']
    total = 0
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for _summary, rows in statements:
            for r in rows:
                w.writerow(r)
                total += 1
    print(json.dumps({'file': args.xlsx, 'csv': out, 'rows': total,
                      'statements': [s for s, _rows in statements]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
