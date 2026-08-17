from django.test import TestCase
from django.utils import timezone
import datetime

from newsfeed.models import FeedItem, FeedItemManager


def make_item(**overrides):
    defaults = dict(
        scope=FeedItem.Scope.CHURCH, item_type=FeedItem.ItemType.NEWS,
        title='Sunday Service', summary='Join us', body='Full details here.',
        expires_at=timezone.now() + datetime.timedelta(days=7),
    )
    defaults.update(overrides)
    return FeedItem.objects.create(**defaults)


class FeedItemModelTests(TestCase):
    def test_slug_auto_generated_from_title(self):
        item = make_item(title='Easter Sunday Service')
        self.assertEqual(item.slug, 'easter-sunday-service')

    def test_duplicate_title_gets_unique_suffixed_slug(self):
        first = make_item(title='Same Title')
        second = make_item(title='Same Title')
        self.assertEqual(first.slug, 'same-title')
        self.assertEqual(second.slug, 'same-title-2')

    def test_live_item_type_is_auto_pinned(self):
        item = make_item(item_type=FeedItem.ItemType.LIVE, title='We are live')
        self.assertTrue(item.is_pinned)

    def test_non_live_item_not_auto_pinned(self):
        item = make_item(title='Just news')
        self.assertFalse(item.is_pinned)

    def test_is_expired_property(self):
        expired = make_item(title='Old news', expires_at=timezone.now() - datetime.timedelta(days=1))
        active = make_item(title='Fresh news', expires_at=timezone.now() + datetime.timedelta(days=1))
        self.assertTrue(expired.is_expired)
        self.assertFalse(active.is_expired)

    def test_get_absolute_url_uses_slug(self):
        item = make_item(title='Slug Check')
        self.assertIn(item.slug, item.get_absolute_url())


class FeedItemManagerActiveTests(TestCase):
    def test_active_excludes_expired(self):
        make_item(title='Expired', expires_at=timezone.now() - datetime.timedelta(days=1))
        fresh = make_item(title='Fresh')
        results = list(FeedItemManager.active())
        self.assertIn(fresh, results)
        self.assertEqual(len(results), 1)

    def test_active_excludes_inactive(self):
        make_item(title='Hidden', is_active=False)
        results = list(FeedItemManager.active())
        self.assertEqual(len(results), 0)

    def test_active_excludes_not_yet_published(self):
        make_item(title='Future', published_at=timezone.now() + datetime.timedelta(days=1))
        results = list(FeedItemManager.active())
        self.assertEqual(len(results), 0)

    def test_active_filters_by_scope(self):
        make_item(title='Church Item', scope=FeedItem.Scope.CHURCH)
        make_item(title='Gym Item', scope=FeedItem.Scope.GYM)
        church_results = list(FeedItemManager.active(scope=FeedItem.Scope.CHURCH))
        self.assertEqual(len(church_results), 1)
        self.assertEqual(church_results[0].title, 'Church Item')
