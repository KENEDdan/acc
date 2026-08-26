from django.db.models import Sum

_CSV_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def sanitize_csv_cell(value):
    """Neutralizes CSV/formula injection (OWASP CSV Injection): a cell that
    starts with =, +, -, @, tab, or CR can be read as a formula by Excel/
    LibreOffice when the exported file is opened. Prefixing with a single
    quote keeps the value literal without changing what's displayed."""
    text = '' if value is None else str(value)
    if text.startswith(_CSV_FORMULA_PREFIXES):
        return "'" + text
    return text


def sanitize_csv_row(row):
    return [sanitize_csv_cell(cell) for cell in row]


def currency_breakdown(income_qs, expense_qs):
    data = {}
    for row in income_qs:
        entry = data.setdefault(row['currency'], {'currency': row['currency'], 'income': 0, 'expense': 0})
        entry['income'] = row['total'] or 0
    for row in expense_qs:
        entry = data.setdefault(row['currency'], {'currency': row['currency'], 'income': 0, 'expense': 0})
        entry['expense'] = row['total'] or 0
    if not data:
        data['SSP'] = {'currency': 'SSP', 'income': 0, 'expense': 0}
    for entry in data.values():
        entry['balance'] = entry['income'] - entry['expense']
    return sorted(data.values(), key=lambda e: e['currency'])


def period_breakdown(qs, trunc_func, limit=None):
    """Groups a FinanceRecord-shaped queryset (type/amount/currency/date) into
    income/expense/balance rows per period (day/week/month/year) and currency,
    most recent first. Used for the daily/weekly/monthly/annual finance reports."""
    income_qs = (qs.filter(type='income').annotate(period=trunc_func('date'))
                 .values('period', 'currency').annotate(total=Sum('amount')))
    expense_qs = (qs.filter(type='expense').annotate(period=trunc_func('date'))
                  .values('period', 'currency').annotate(total=Sum('amount')))
    data = {}
    for row in income_qs:
        key = (row['period'], row['currency'])
        entry = data.setdefault(key, {'period': row['period'], 'currency': row['currency'], 'income': 0, 'expense': 0})
        entry['income'] = row['total'] or 0
    for row in expense_qs:
        key = (row['period'], row['currency'])
        entry = data.setdefault(key, {'period': row['period'], 'currency': row['currency'], 'income': 0, 'expense': 0})
        entry['expense'] = row['total'] or 0
    for entry in data.values():
        entry['balance'] = entry['income'] - entry['expense']
    rows = sorted(data.values(), key=lambda e: (e['period'], e['currency']), reverse=True)
    return rows[:limit] if limit else rows