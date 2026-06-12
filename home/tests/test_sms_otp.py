"""SMS OTP helper — mod dev vs live."""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings

from home.sms_otp import (
    ensure_signup_otp_sent,
    is_sms_otp_live,
    normalize_phone_digits,
    verify_sms_code,
)


class SmsOtpHelperTests(TestCase):
    def test_normalize_phone_ro(self):
        self.assertEqual(normalize_phone_digits("+40", "0753017411"), "40753017411")
        self.assertEqual(normalize_phone_digits("+40", "753017411"), "40753017411")

    @override_settings(SMS_OTP_ENABLED=False)
    def test_dev_mode_accepts_111111(self):
        ok, err = verify_sms_code("111111")
        self.assertTrue(ok)
        self.assertEqual(err, "")

    @override_settings(SMS_OTP_ENABLED=False)
    def test_dev_mode_rejects_wrong(self):
        ok, err = verify_sms_code("000000")
        self.assertFalse(ok)

    @override_settings(SMS_OTP_ENABLED=True, EUADOPT_SMSAPI_TOKEN="tok")
    def test_live_mode_uses_cache(self):
        rf = RequestFactory()
        request = rf.get("/")
        request.session = self.client.session
        request.session.save()
        cache_key_part = request.session.session_key
        cache.set(f"euadopt:sms_otp:signup:{cache_key_part}", "654321", 300)
        ok, _ = verify_sms_code("654321", request=request, purpose="signup")
        self.assertTrue(ok)

    @override_settings(SMS_OTP_ENABLED=True, EUADOPT_SMSAPI_TOKEN="tok")
    def test_is_live_with_token(self):
        self.assertTrue(is_sms_otp_live())

    @override_settings(SMS_OTP_ENABLED=True, EUADOPT_SMSAPI_TOKEN="")
    def test_not_live_without_token(self):
        self.assertFalse(is_sms_otp_live())

    @override_settings(SMS_OTP_ENABLED=True, EUADOPT_SMSAPI_TOKEN="tok")
    @patch("home.sms_otp._send_sms", return_value=(True, None))
    def test_ensure_signup_sends_once(self, mock_send):
        rf = RequestFactory()
        request = rf.get("/")
        request.session = self.client.session
        request.session.save()
        data = {"phone_country": "+40", "phone": "0753017411"}
        ok, err = ensure_signup_otp_sent(request, data)
        self.assertTrue(ok)
        self.assertIsNone(err)
        mock_send.assert_called_once()
        ok2, _ = ensure_signup_otp_sent(request, data)
        self.assertTrue(ok2)
        mock_send.assert_called_once()
