from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from home.models import TransportVeterinaryRequest
from home.transport_eu_inbox import TRANSPORT_EU_INBOX, send_eu_transport_request_to_inbox


class TransportEuInboxTests(TestCase):
    @override_settings(DEFAULT_FROM_EMAIL="noreply@eu-adopt.ro")
    @patch("home.transport_eu_inbox.send_mail_text_and_html")
    def test_sends_to_hyphen_inbox_with_reply_to(self, mock_send):
        User = get_user_model()
        u = User.objects.create_user(username="eu_tr", email="adopter@example.com", password="x")
        tvr = TransportVeterinaryRequest.objects.create(
            user=u,
            country="DE",
            judet="Brașov",
            oras="Codlea",
            plecare="Shelter gate",
            sosire="Munich hub",
            nr_caini=2,
            route_scope=TransportVeterinaryRequest.ROUTE_INTERNATIONAL,
            urgency_window=TransportVeterinaryRequest.URGENCY_FLEX,
        )
        rf = RequestFactory()
        req = rf.get("/", HTTP_HOST="euadopt.com")
        ok = send_eu_transport_request_to_inbox(req, tvr)
        self.assertTrue(ok)
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        self.assertEqual(args[3], [TRANSPORT_EU_INBOX])
        self.assertEqual(TRANSPORT_EU_INBOX, "transport@eu-adopt.ro")
        self.assertEqual(kwargs.get("reply_to"), ["adopter@example.com"])
        self.assertIn("EU-Adopt", args[1])
        self.assertIn("DE", args[1])


class TransportEuInboxLabelsTests(SimpleTestCase):
    def test_intro_mentions_find_or_not(self):
        from home.eu_ui_labels import eu_ui_label

        intro = eu_ui_label("transport_t1_intro")
        self.assertIn("transport@eu-adopt.ro", intro)
        self.assertIn("If we find", intro)
        self.assertIn("shelter", intro.lower())
        ok = eu_ui_label("transport_submit_ok")
        self.assertIn("sent to our team", ok)
