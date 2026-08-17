from django.test import TestCase

from finance.utils import currency_breakdown, period_breakdown
from church.models import FinanceRecord
from django.db.models.functions import TruncMonth
import datetime


class CurrencyBreakdownTests(TestCase):
    def test_empty_querysets_default_to_zeroed_ssp_row(self):
        rows = currency_breakdown([], [])
        self.assertEqual(rows, [{'currency': 'SSP', 'income': 0, 'expense': 0, 'balance': 0}])

    def test_merges_income_and_expense_per_currency(self):
        income_qs = [{'currency': 'SSP', 'total': 500}, {'currency': 'USD', 'total': 100}]
        expense_qs = [{'currency': 'SSP', 'total': 200}]
        rows = {r['currency']: r for r in currency_breakdown(income_qs, expense_qs)}

        self.assertEqual(rows['SSP']['income'], 500)
        self.assertEqual(rows['SSP']['expense'], 200)
        self.assertEqual(rows['SSP']['balance'], 300)
        self.assertEqual(rows['USD']['income'], 100)
        self.assertEqual(rows['USD']['expense'], 0)
        self.assertEqual(rows['USD']['balance'], 100)

    def test_sorted_by_currency(self):
        rows = currency_breakdown(
            [{'currency': 'USD', 'total': 1}, {'currency': 'SSP', 'total': 1}], [],
        )
        self.assertEqual([r['currency'] for r in rows], ['SSP', 'USD'])


class PeriodBreakdownTests(TestCase):
    def test_groups_by_period_and_currency_with_balance(self):
        FinanceRecord.objects.create(
            type='income', income_category='tithes', amount=1000, currency='SSP',
            date=datetime.date(2026, 1, 15),
        )
        FinanceRecord.objects.create(
            type='expense', expense_category='transport', amount=300, currency='SSP',
            date=datetime.date(2026, 1, 20),
        )
        FinanceRecord.objects.create(
            type='income', income_category='donation', amount=50, currency='USD',
            date=datetime.date(2026, 2, 1),
        )

        rows = period_breakdown(FinanceRecord.objects.all(), TruncMonth)
        by_key = {(r['period'], r['currency']): r for r in rows}

        jan_ssp = by_key[(datetime.date(2026, 1, 1), 'SSP')]
        self.assertEqual(jan_ssp['income'], 1000)
        self.assertEqual(jan_ssp['expense'], 300)
        self.assertEqual(jan_ssp['balance'], 700)

        feb_usd = by_key[(datetime.date(2026, 2, 1), 'USD')]
        self.assertEqual(feb_usd['income'], 50)
        self.assertEqual(feb_usd['expense'], 0)

    def test_most_recent_period_first(self):
        FinanceRecord.objects.create(type='income', income_category='tithes', amount=1, currency='SSP', date=datetime.date(2026, 1, 1))
        FinanceRecord.objects.create(type='income', income_category='tithes', amount=1, currency='SSP', date=datetime.date(2026, 3, 1))
        rows = period_breakdown(FinanceRecord.objects.all(), TruncMonth)
        self.assertGreater(rows[0]['period'], rows[-1]['period'])

    def test_limit_caps_row_count(self):
        for month in range(1, 6):
            FinanceRecord.objects.create(type='income', income_category='tithes', amount=1, currency='SSP', date=datetime.date(2026, month, 1))
        rows = period_breakdown(FinanceRecord.objects.all(), TruncMonth, limit=2)
        self.assertEqual(len(rows), 2)
