import datetime

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from aff.models import AssistanceRequest, FinanceRecord, CashReconciliation

User = get_user_model()

VALID_REQUEST_DATA = {
    'full_name': 'Needy Member', 'request_date': '2026-01-10', 'tel': '0911111111',
    'sex': 'male', 'marital_status': 'single', 'residential_address': 'Juba',
    'membership_type': 'full_time', 'how_church_can_help': 'Please help with fees',
    'need_category': 'school_fees', 'amount_have': '0', 'amount_requested': '500',
    'currency': 'SSP', 'help_directed_to': 'me',
}


class CashReconciliationModelTests(TestCase):
    def test_discrepancy_computed_on_save(self):
        rec = CashReconciliation.objects.create(
            date=datetime.date(2026, 1, 1), cash_at_hand=1000, system_recorded_balance=950, source='Office safe',
        )
        self.assertEqual(rec.discrepancy, 50)

    def test_discrepancy_recomputed_on_update(self):
        rec = CashReconciliation.objects.create(
            date=datetime.date(2026, 1, 1), cash_at_hand=1000, system_recorded_balance=1000, source='Office safe',
        )
        self.assertEqual(rec.discrepancy, 0)
        rec.cash_at_hand = 800
        rec.save()
        self.assertEqual(rec.discrepancy, -200)


class AssistanceRequestWorkflowTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='needymember', password='x', role=User.Role.MEMBER)
        self.aff_finance = User.objects.create_user(username='afffin', password='x', role='aff_finance', two_factor_enabled=True)
        self.superadmin = User.objects.create_user(username='affsuper', password='x', role='superadmin', two_factor_enabled=True)

    def test_member_submission_starts_as_submitted_status(self):
        c = Client()
        c.force_login(self.member)
        c.post('/aff/requests/new/', VALID_REQUEST_DATA)
        req = AssistanceRequest.objects.get()
        self.assertEqual(req.status, AssistanceRequest.Status.SUBMITTED)
        self.assertEqual(req.filled_by, self.member)

    def test_finance_admin_can_forward_a_submitted_request(self):
        req = AssistanceRequest.objects.create(status=AssistanceRequest.Status.SUBMITTED, **{
            **{k: v for k, v in VALID_REQUEST_DATA.items() if k != 'request_date'},
            'request_date': datetime.date(2026, 1, 10),
        })
        c = Client()
        c.force_login(self.aff_finance)
        c.post(f'/aff/requests/{req.pk}/forward/')
        req.refresh_from_db()
        self.assertEqual(req.status, AssistanceRequest.Status.PENDING)

    def test_only_superadmin_can_review_a_request(self):
        req = AssistanceRequest.objects.create(status=AssistanceRequest.Status.PENDING, **{
            **{k: v for k, v in VALID_REQUEST_DATA.items() if k != 'request_date'},
            'request_date': datetime.date(2026, 1, 10),
        })
        c = Client()
        c.force_login(self.aff_finance)
        response = c.get(f'/aff/requests/{req.pk}/review/')
        self.assertEqual(response.status_code, 302)  # not superadmin, bounced

        c.force_login(self.superadmin)
        response = c.post(f'/aff/requests/{req.pk}/review/', {'decision': 'approved', 'review_notes': ''})
        req.refresh_from_db()
        self.assertEqual(req.status, AssistanceRequest.Status.APPROVED)
        self.assertEqual(req.reviewed_by, self.superadmin)

    def test_declining_requires_a_reason(self):
        req = AssistanceRequest.objects.create(status=AssistanceRequest.Status.PENDING, **{
            **{k: v for k, v in VALID_REQUEST_DATA.items() if k != 'request_date'},
            'request_date': datetime.date(2026, 1, 10),
        })
        c = Client()
        c.force_login(self.superadmin)
        c.post(f'/aff/requests/{req.pk}/review/', {'decision': 'declined', 'review_notes': ''})
        req.refresh_from_db()
        self.assertEqual(req.status, AssistanceRequest.Status.PENDING)  # unchanged, form was invalid

    def test_disbursing_an_approved_request_creates_expense_and_marks_disbursed(self):
        req = AssistanceRequest.objects.create(status=AssistanceRequest.Status.APPROVED, **{
            **{k: v for k, v in VALID_REQUEST_DATA.items() if k != 'request_date'},
            'request_date': datetime.date(2026, 1, 10),
        })
        c = Client()
        c.force_login(self.aff_finance)
        c.post(f'/aff/requests/{req.pk}/disburse/', {'disbursed_amount': '500', 'disbursed_date': '2026-01-20'})

        req.refresh_from_db()
        self.assertEqual(req.status, AssistanceRequest.Status.DISBURSED)
        self.assertEqual(req.disbursed_amount, 500)
        entry = FinanceRecord.objects.get(related_request=req)
        self.assertEqual(entry.type, FinanceRecord.Type.EXPENSE)
        self.assertEqual(entry.amount, 500)

    def test_cannot_disburse_a_request_that_is_not_approved(self):
        req = AssistanceRequest.objects.create(status=AssistanceRequest.Status.PENDING, **{
            **{k: v for k, v in VALID_REQUEST_DATA.items() if k != 'request_date'},
            'request_date': datetime.date(2026, 1, 10),
        })
        c = Client()
        c.force_login(self.aff_finance)
        response = c.post(f'/aff/requests/{req.pk}/disburse/', {'disbursed_amount': '500', 'disbursed_date': '2026-01-20'})
        self.assertEqual(response.status_code, 404)


class AffFinanceConfirmFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='afffin2', password='x', role='aff_finance', two_factor_enabled=True)
        self.client = Client()
        self.client.force_login(self.user)

    def test_submitting_without_confirm_shows_preview_and_does_not_save(self):
        response = self.client.post('/aff/finance/new/', {
            'type': 'income', 'income_category': 'donations_grants', 'amount': '250', 'currency': 'SSP',
            'date': '2026-01-10',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'aff/finance_confirm.html')
        self.assertEqual(FinanceRecord.objects.count(), 0)

    def test_confirm_flag_saves_the_record(self):
        response = self.client.post('/aff/finance/new/', {
            'type': 'income', 'income_category': 'donations_grants', 'amount': '250', 'currency': 'SSP',
            'date': '2026-01-10', 'confirm': '1',
        })
        self.assertRedirects(response, '/aff/dashboard/finance/')
        self.assertEqual(FinanceRecord.objects.count(), 1)
