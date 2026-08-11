"""Teste postări Facebook (Graph API mock)."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from home.facebook_page_post import (
    enqueue_animal,
    enqueue_campanie,
    flush_pending,
    process_outbound_row,
)
from home.models import AnimalListing, CampanieSterilizare, FacebookOutboundPost

User = get_user_model()


@override_settings(
    FACEBOOK_AUTO_POST_ENABLED=True,
    FACEBOOK_PAGE_ID="61588044314372",
    FACEBOOK_PAGE_ACCESS_TOKEN="test-token",
    FACEBOOK_MAX_POSTS_PER_DAY=10,
    SITE_BASE_URL="https://eu-adopt.ro",
)
class FacebookOutboundTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("fb_owner", "fb@test.local", "x")

    def _animal(self, **kwargs):
        defaults = dict(
            owner=self.user,
            name="Rex",
            species="dog",
            age_label="2 ani",
            city="Roman",
            county="Neamț",
            is_published=True,
        )
        defaults.update(kwargs)
        return AnimalListing.objects.create(**defaults)

    @patch("home.facebook_page_post._graph_post")
    def test_enqueue_animal_posts_immediately(self, mock_graph):
        mock_graph.return_value = {"id": "61588044314372_111", "post_id": "61588044314372_111"}
        listing = self._animal()
        row = enqueue_animal(listing, schedule=False)
        self.assertIsNotNone(row)
        result = process_outbound_row(row.pk)
        self.assertTrue(result.ok)
        row.refresh_from_db()
        self.assertEqual(row.status, FacebookOutboundPost.STATUS_POSTED)
        self.assertEqual(row.facebook_post_id, "61588044314372_111")
        mock_graph.assert_called()

    @patch("home.facebook_page_post._graph_post")
    def test_daily_cap_defers(self, mock_graph):
        mock_graph.return_value = {"id": "x", "post_id": "x"}
        now = timezone.now()
        for i in range(10):
            FacebookOutboundPost.objects.create(
                kind=FacebookOutboundPost.KIND_ANIMAL,
                object_id=9000 + i,
                status=FacebookOutboundPost.STATUS_POSTED,
                facebook_post_id=f"p{i}",
                posted_at=now,
            )
        listing = self._animal(name="Max")
        row = enqueue_animal(listing, schedule=False)
        result = process_outbound_row(row.pk)
        self.assertTrue(result.deferred)
        row.refresh_from_db()
        self.assertEqual(row.status, FacebookOutboundPost.STATUS_PENDING)
        mock_graph.assert_not_called()

    @patch("home.facebook_page_post._graph_post")
    def test_campanie_enqueue(self, mock_graph):
        mock_graph.return_value = {"id": "c1", "post_id": "c1"}
        photo = SimpleUploadedFile("c.jpg", b"\xff\xd8\xff\xd9", content_type="image/jpeg")
        camp = CampanieSterilizare.objects.create(
            user=self.user,
            judet="Neamț",
            judet_slug="neamt",
            localitate="Roman",
            species_dogs=True,
            species_cats=False,
            date_start=date.today(),
            date_end=date.today() + timedelta(days=3),
            photo=photo,
        )
        row = enqueue_campanie(camp, schedule=False)
        result = process_outbound_row(row.pk)
        self.assertTrue(result.ok)
        row.refresh_from_db()
        self.assertEqual(row.status, FacebookOutboundPost.STATUS_POSTED)

    @override_settings(FACEBOOK_AUTO_POST_ENABLED=False)
    def test_disabled_skips_enqueue(self):
        listing = self._animal()
        self.assertIsNone(enqueue_animal(listing))
        self.assertEqual(FacebookOutboundPost.objects.count(), 0)

    @patch("home.facebook_page_post._graph_post")
    def test_flush_pending(self, mock_graph):
        mock_graph.return_value = {"post_id": "flush1", "id": "flush1"}
        listing = self._animal(name="Luna", species="cat")
        enqueue_animal(listing, schedule=False)
        stats = flush_pending()
        self.assertEqual(stats["posted"], 1)
