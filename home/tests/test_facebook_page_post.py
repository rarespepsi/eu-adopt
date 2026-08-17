"""Teste postări Facebook multi-piață + anti-buclă mirror."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from home.facebook_page_post import (
    enqueue_animal,
    enqueue_campanie,
    flush_pending,
    process_delivery,
    process_outbound_row,
)
from home.facebook_ro_mirror import ingest_ro_posts, process_pending_inbounds
from home.models import (
    AnimalListing,
    CampanieSterilizare,
    FacebookOutboundDelivery,
    FacebookOutboundPost,
    FacebookRoInboundPost,
)

User = get_user_model()


@override_settings(
    FACEBOOK_AUTO_POST_ENABLED=True,
    FACEBOOK_PAGE_ID="970069896196143",
    FACEBOOK_PAGE_ACCESS_TOKEN="test-token-ro",
    FACEBOOK_PAGE_ACCESS_TOKEN_RO="test-token-ro",
    FACEBOOK_PAGE_ID_DE="",
    FACEBOOK_PAGE_ACCESS_TOKEN_DE="",
    FACEBOOK_PAGE_ID_FR="",
    FACEBOOK_PAGE_ACCESS_TOKEN_FR="",
    FACEBOOK_PAGE_ID_ES="",
    FACEBOOK_PAGE_ACCESS_TOKEN_ES="",
    FACEBOOK_PAGE_ID_COM="",
    FACEBOOK_PAGE_ACCESS_TOKEN_COM="",
    FACEBOOK_MAX_POSTS_PER_DAY=10,
    FACEBOOK_RO_MIRROR_ENABLED=False,
    SITE_BASE_URL="https://eu-adopt.ro",
    EUADOPT_GEMINI_API_KEY="",
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

    @patch("home.facebook_page_post._graph_request")
    def test_enqueue_animal_posts_ro_delivery(self, mock_graph):
        mock_graph.return_value = {"id": "970069896196143_111", "post_id": "970069896196143_111"}
        listing = self._animal()
        row = enqueue_animal(listing, schedule=False)
        self.assertIsNotNone(row)
        self.assertEqual(row.deliveries.count(), 1)
        self.assertEqual(row.deliveries.get().market, "ro")
        result = process_outbound_row(row.pk)
        self.assertTrue(result.ok)
        row.refresh_from_db()
        d = row.deliveries.get(market="ro")
        self.assertEqual(d.status, FacebookOutboundDelivery.STATUS_POSTED)
        self.assertEqual(d.facebook_post_id, "970069896196143_111")

    @patch("home.facebook_page_post._graph_request")
    def test_daily_cap_defers_ro(self, mock_graph):
        mock_graph.return_value = {"id": "x", "post_id": "x"}
        now = timezone.now()
        for i in range(10):
            src = FacebookOutboundPost.objects.create(
                kind=FacebookOutboundPost.KIND_ANIMAL,
                object_id=9000 + i,
                status=FacebookOutboundPost.STATUS_POSTED,
            )
            FacebookOutboundDelivery.objects.create(
                outbound=src,
                market="ro",
                status=FacebookOutboundDelivery.STATUS_POSTED,
                facebook_post_id=f"p{i}",
                posted_at=now,
            )
        listing = self._animal(name="Max")
        row = enqueue_animal(listing, schedule=False)
        result = process_outbound_row(row.pk)
        self.assertTrue(result.deferred)
        d = row.deliveries.get(market="ro")
        self.assertEqual(d.status, FacebookOutboundDelivery.STATUS_PENDING)
        mock_graph.assert_not_called()

    @patch("home.facebook_page_post._graph_request")
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
        self.assertEqual(row.deliveries.get(market="ro").status, FacebookOutboundDelivery.STATUS_POSTED)

    @override_settings(FACEBOOK_AUTO_POST_ENABLED=False)
    def test_disabled_skips_enqueue(self):
        listing = self._animal()
        self.assertIsNone(enqueue_animal(listing))
        self.assertEqual(FacebookOutboundPost.objects.count(), 0)

    @patch("home.facebook_page_post._graph_request")
    def test_flush_pending(self, mock_graph):
        mock_graph.return_value = {"post_id": "flush1", "id": "flush1"}
        listing = self._animal(name="Luna", species="cat")
        enqueue_animal(listing, schedule=False)
        stats = flush_pending()
        self.assertEqual(stats["posted"], 1)

    @override_settings(
        FACEBOOK_PAGE_ID_DE="de-page",
        FACEBOOK_PAGE_ACCESS_TOKEN_DE="de-token",
        FACEBOOK_PAGE_ID_FR="fr-page",
        FACEBOOK_PAGE_ACCESS_TOKEN_FR="fr-token",
    )
    @patch("home.facebook_page_post.translate_facebook_message", side_effect=lambda t, target_lang: f"[{target_lang}] {t}")
    @patch("home.facebook_page_post._graph_request")
    def test_multi_market_isolated_failure(self, mock_graph, _tr):
        def _side_effect(**kwargs):
            page_id = kwargs.get("page_id")
            if page_id == "fr-page":
                raise RuntimeError("FR boom")
            return {"id": f"{page_id}_ok", "post_id": f"{page_id}_ok"}

        mock_graph.side_effect = _side_effect
        listing = self._animal(name="Isolated")
        row = enqueue_animal(listing, schedule=False)
        markets = set(row.deliveries.values_list("market", flat=True))
        self.assertEqual(markets, {"ro", "de", "fr"})
        process_outbound_row(row.pk)
        row.refresh_from_db()
        self.assertEqual(row.deliveries.get(market="ro").status, "posted")
        self.assertEqual(row.deliveries.get(market="de").status, "posted")
        self.assertEqual(row.deliveries.get(market="fr").status, "failed")
        self.assertEqual(row.status, FacebookOutboundPost.STATUS_PARTIAL)


@override_settings(
    FACEBOOK_AUTO_POST_ENABLED=True,
    FACEBOOK_PAGE_ID="970069896196143",
    FACEBOOK_PAGE_ACCESS_TOKEN="test-token-ro",
    FACEBOOK_PAGE_ACCESS_TOKEN_RO="test-token-ro",
    FACEBOOK_PAGE_ID_DE="de-page",
    FACEBOOK_PAGE_ACCESS_TOKEN_DE="de-token",
    FACEBOOK_PAGE_ID_FR="",
    FACEBOOK_PAGE_ACCESS_TOKEN_FR="",
    FACEBOOK_PAGE_ID_ES="",
    FACEBOOK_PAGE_ACCESS_TOKEN_ES="",
    FACEBOOK_PAGE_ID_COM="",
    FACEBOOK_PAGE_ACCESS_TOKEN_COM="",
    FACEBOOK_RO_MIRROR_ENABLED=True,
    FACEBOOK_RO_MIRROR_MAX_PER_RUN=10,
    SITE_BASE_URL="https://eu-adopt.ro",
    EUADOPT_GEMINI_API_KEY="",
)
class FacebookRoMirrorTests(TestCase):
    def test_ingest_skips_auto_ro_posts(self):
        src = FacebookOutboundPost.objects.create(
            kind=FacebookOutboundPost.KIND_ANIMAL,
            object_id=1,
            status=FacebookOutboundPost.STATUS_POSTED,
        )
        FacebookOutboundDelivery.objects.create(
            outbound=src,
            market="ro",
            status=FacebookOutboundDelivery.STATUS_POSTED,
            facebook_post_id="970069896196143_auto1",
            posted_at=timezone.now(),
        )
        stats = ingest_ro_posts(
            [
                {"id": "970069896196143_auto1", "message": "auto"},
                {"id": "970069896196143_manual1", "message": "Manual post RO", "permalink_url": "https://fb.me/x"},
            ]
        )
        self.assertEqual(stats["skipped_auto"], 1)
        self.assertEqual(stats["new"], 1)
        inbound = FacebookRoInboundPost.objects.get(source_fb_post_id="970069896196143_manual1")
        self.assertEqual(inbound.status, FacebookRoInboundPost.STATUS_PENDING)
        auto = FacebookRoInboundPost.objects.get(source_fb_post_id="970069896196143_auto1")
        self.assertEqual(auto.status, FacebookRoInboundPost.STATUS_SKIPPED_AUTO)

    @patch("home.facebook_page_post.translate_facebook_message", side_effect=lambda t, target_lang: t)
    @patch("home.facebook_page_post._graph_request")
    def test_mirror_only_to_non_ro(self, mock_graph, _tr):
        mock_graph.return_value = {"id": "de_post", "post_id": "de_post"}
        inbound = FacebookRoInboundPost.objects.create(
            source_fb_post_id="manual_99",
            message="Salut din România https://eu-adopt.ro/pets/1/",
            status=FacebookRoInboundPost.STATUS_PENDING,
        )
        stats = process_pending_inbounds(limit=5)
        self.assertEqual(stats["mirrored"], 1)
        inbound.refresh_from_db()
        self.assertEqual(inbound.status, FacebookRoInboundPost.STATUS_PROCESSED)
        out = inbound.outbound
        self.assertIsNotNone(out)
        self.assertEqual(out.kind, FacebookOutboundPost.KIND_RO_MIRROR)
        markets = set(out.deliveries.values_list("market", flat=True))
        self.assertEqual(markets, {"de"})
        self.assertNotIn("ro", markets)

    def test_duplicate_ingest_idempotent(self):
        ingest_ro_posts([{"id": "same_1", "message": "a"}])
        stats = ingest_ro_posts([{"id": "same_1", "message": "a"}])
        self.assertEqual(stats["existing"], 1)
        self.assertEqual(FacebookRoInboundPost.objects.filter(source_fb_post_id="same_1").count(), 1)

    @override_settings(FACEBOOK_RO_MIRROR_SINCE="2026-08-11T20:00:00+00:00")
    def test_ingest_skips_posts_before_since(self):
        stats = ingest_ro_posts(
            [
                {
                    "id": "old_1",
                    "message": "istoric",
                    "created_time": "2026-08-10T12:00:00+0000",
                },
                {
                    "id": "new_1",
                    "message": "nou dupa activare",
                    "created_time": "2026-08-11T21:00:00+0000",
                },
            ]
        )
        self.assertEqual(stats["skipped_before_since"], 1)
        self.assertEqual(stats["new"], 1)
        old = FacebookRoInboundPost.objects.get(source_fb_post_id="old_1")
        self.assertEqual(old.status, FacebookRoInboundPost.STATUS_SKIPPED_AUTO)
        self.assertEqual(old.skip_reason, "before_mirror_since")
        new = FacebookRoInboundPost.objects.get(source_fb_post_id="new_1")
        self.assertEqual(new.status, FacebookRoInboundPost.STATUS_PENDING)


class _FakeGraphResp:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FacebookPageTokenResolveTests(TestCase):
    def setUp(self):
        from home.facebook_markets import clear_page_token_cache

        clear_page_token_cache()

    def tearDown(self):
        from home.facebook_markets import clear_page_token_cache

        clear_page_token_cache()

    def test_non_eaa_token_skips_graph(self):
        from home.facebook_markets import resolve_page_access_token

        with patch("home.facebook_markets.urllib.request.urlopen") as mock_open:
            tok = resolve_page_access_token("970069896196143", "test-token-ro")
        self.assertEqual(tok, "test-token-ro")
        mock_open.assert_not_called()

    @patch("home.facebook_markets.urllib.request.urlopen")
    def test_system_user_token_uses_page_token_from_accounts(self, mock_open):
        from home.facebook_markets import resolve_page_access_token

        mock_open.return_value = _FakeGraphResp(
            {
                "data": [
                    {"id": "970069896196143", "access_token": "EAA_PAGE_RO"},
                    {"id": "1156775504195672", "access_token": "EAA_PAGE_DE"},
                ]
            }
        )
        su = "EAA_SYSTEM_USER_TOKEN"
        self.assertEqual(resolve_page_access_token("970069896196143", su), "EAA_PAGE_RO")
        self.assertEqual(resolve_page_access_token("1156775504195672", su), "EAA_PAGE_DE")
        mock_open.assert_called_once()

    @patch("home.facebook_markets.urllib.request.urlopen")
    def test_unknown_page_falls_back_to_env_token(self, mock_open):
        from home.facebook_markets import resolve_page_access_token

        mock_open.return_value = _FakeGraphResp({"data": [{"id": "other", "access_token": "EAA_X"}]})
        su = "EAA_SYSTEM_USER_TOKEN"
        self.assertEqual(resolve_page_access_token("970069896196143", su), su)

    @patch("home.facebook_markets.urllib.request.urlopen", side_effect=OSError("offline"))
    def test_accounts_error_falls_back(self, _mock_open):
        from home.facebook_markets import resolve_page_access_token

        su = "EAA_SYSTEM_USER_TOKEN"
        self.assertEqual(resolve_page_access_token("970069896196143", su), su)
