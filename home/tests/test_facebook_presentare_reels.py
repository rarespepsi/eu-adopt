from django.test import SimpleTestCase

from home.facebook_presentare_reels import (
    PRESENTARE_REELS,
    presentare_repost_message,
    reel_by_key,
    reel_for_weekday,
)


class PresentareReelsTests(SimpleTestCase):
    def test_two_reels_memorized(self):
        self.assertEqual(len(PRESENTARE_REELS), 2)
        self.assertIn('facebook.com/reel/', PRESENTARE_REELS[0].reel_url)
        self.assertIn('facebook.com/reel/', PRESENTARE_REELS[1].reel_url)

    def test_weekday_mapping(self):
        self.assertEqual(reel_for_weekday(0).key, 'lun')
        self.assertEqual(reel_for_weekday(2).key, 'mie')
        self.assertIsNone(reel_for_weekday(1))

    def test_key_aliases(self):
        self.assertEqual(reel_by_key('mon').key, 'lun')
        self.assertEqual(reel_by_key('wed').key, 'mie')

    def test_message_has_links(self):
        msg = presentare_repost_message(PRESENTARE_REELS[0])
        self.assertIn('eu-adopt.ro', msg)
        self.assertIn(PRESENTARE_REELS[0].reel_url, msg)
