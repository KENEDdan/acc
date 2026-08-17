import json

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from newsfeed.models import FeedItem
from django.utils import timezone
import datetime

User = get_user_model()


class HomeViewTests(TestCase):
    def test_home_page_loads(self):
        c = Client()
        response = c.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_context_counts_active_members(self):
        from church.models import Member
        Member.objects.create(
            full_name='Active One', address='x', contact_phone='0900',
            date_of_birth=datetime.date(1990, 1, 1), gender='male', marital_status='single', is_active=True,
        )
        Member.objects.create(
            full_name='Inactive One', address='x', contact_phone='0900',
            date_of_birth=datetime.date(1990, 1, 1), gender='male', marital_status='single', is_active=False,
        )
        response = Client().get('/')
        self.assertEqual(response.context['member_count'], 1)


class SearchViewTests(TestCase):
    def setUp(self):
        FeedItem.objects.create(
            scope=FeedItem.Scope.MAIN, item_type=FeedItem.ItemType.NEWS, title='Christmas Service',
            summary='s', body='b', expires_at=timezone.now() + datetime.timedelta(days=1),
        )
        FeedItem.objects.create(
            scope=FeedItem.Scope.MAIN, item_type=FeedItem.ItemType.NEWS, title='Easter Program',
            summary='s', body='b', expires_at=timezone.now() + datetime.timedelta(days=1),
        )

    def test_search_matches_title(self):
        response = Client().get('/search/', {'q': 'Christmas'})
        titles = [r.title for r in response.context['results']]
        self.assertEqual(titles, ['Christmas Service'])

    def test_empty_query_returns_no_results(self):
        response = Client().get('/search/', {'q': ''})
        self.assertEqual(list(response.context['results']), [])


class PortalLoginTests(TestCase):
    def test_login_without_2fa_goes_straight_to_dashboard_redirect(self):
        User.objects.create_user(username='plainlogin', password='Sup3rSecure!123', role='church_info')
        c = Client()
        response = c.post('/portal/', {'username': 'plainlogin', 'password': 'Sup3rSecure!123'})
        self.assertRedirects(response, '/dashboard/redirect/', fetch_redirect_response=False)

    def test_login_with_2fa_enabled_redirects_to_verify_without_logging_in_yet(self):
        User.objects.create_user(
            username='has2falogin', password='Sup3rSecure!123', role='superadmin', two_factor_enabled=True,
        )
        c = Client()
        response = c.post('/portal/', {'username': 'has2falogin', 'password': 'Sup3rSecure!123'})
        self.assertRedirects(response, '/account/2fa/verify/', fetch_redirect_response=False)
        self.assertEqual(c.session.get('2fa_user_id'), User.objects.get(username='has2falogin').pk)
        # Not actually authenticated yet — a protected page should still bounce to login.
        response = c.get('/dashboard/redirect/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/portal/', response.url)


class AiAssistantReplyTests(TestCase):
    def test_get_not_allowed(self):
        response = Client().get('/ai-assistant/reply/')
        self.assertEqual(response.status_code, 405)

    def test_known_keyword_returns_matching_faq_answer(self):
        response = Client().post(
            '/ai-assistant/reply/', data=json.dumps({'message': 'what time is sunday service?'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('9:00 AM', response.json()['reply'])

    def test_unknown_message_returns_default_reply(self):
        response = Client().post(
            '/ai-assistant/reply/', data=json.dumps({'message': 'gibberish unrelated text'}),
            content_type='application/json',
        )
        self.assertIn('Thanks for reaching out', response.json()['reply'])

    def test_malformed_json_returns_400(self):
        response = Client().post('/ai-assistant/reply/', data='not json', content_type='application/json')
        self.assertEqual(response.status_code, 400)
