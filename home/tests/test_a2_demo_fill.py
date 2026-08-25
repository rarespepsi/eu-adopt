from django.test import SimpleTestCase
from django.utils import timezone

from home.data import DEMO_DOGS
from home.views import A2_SLOT_COUNT, pad_a2_dogs_with_demo, select_a2_dogs


class A2DemoFillTests(SimpleTestCase):
    def test_demo_pool_has_all_species(self):
        species = {d.get("species") for d in DEMO_DOGS}
        self.assertEqual(species, {"dog", "cat", "other"})
        self.assertEqual(len(DEMO_DOGS), 12)

    def test_pad_empty_fills_twelve(self):
        out = pad_a2_dogs_with_demo([])
        self.assertEqual(len(out), A2_SLOT_COUNT)
        self.assertTrue(all(d.get("a2_filler") for d in out))
        species = {d.get("species") for d in out}
        self.assertEqual(species, {"dog", "cat", "other"})

    def test_pad_short_list(self):
        now = timezone.now()
        short = [
            {"id": 101, "nume": "Rex-real", "species": "dog", "added_at": now, "imagine_fallback": "x"},
            {"id": 102, "nume": "Mia-real", "species": "cat", "added_at": now, "imagine_fallback": "y"},
        ]
        out = pad_a2_dogs_with_demo(short)
        self.assertEqual(len(out), 12)
        self.assertEqual(out[0]["id"], 101)
        self.assertFalse(out[0].get("a2_filler"))
        fillers = [d for d in out if d.get("a2_filler")]
        self.assertEqual(len(fillers), 10)

    def test_no_pad_when_already_twelve(self):
        now = timezone.now()
        full = [{"id": i, "nume": f"P{i}", "added_at": now} for i in range(1, 13)]
        out = pad_a2_dogs_with_demo(full)
        self.assertEqual([d["id"] for d in out], list(range(1, 13)))
        self.assertFalse(any(d.get("a2_filler") for d in out))

    def test_select_then_pad(self):
        now = timezone.now()
        few = [{"id": 7, "nume": "A", "added_at": now}]
        selected = select_a2_dogs(few, limit=12)
        self.assertEqual(len(selected), 1)
        out = pad_a2_dogs_with_demo(selected)
        self.assertEqual(len(out), 12)
