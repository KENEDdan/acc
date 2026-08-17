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