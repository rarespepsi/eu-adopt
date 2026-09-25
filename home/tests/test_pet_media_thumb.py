from django.test import RequestFactory, TestCase, SimpleTestCase
from django.http import Http404
from PIL import Image
import io
import tempfile
from pathlib import Path

from home.pet_media_thumb import (
    THUMB_VERSION,
    _safe_media_relpath,
    estimate_subject_focus,
    is_extreme_aspect,
    letterbox_square,
    pet_media_thumb_view,
    smart_cover_square,
    square_for_thumb,
)


class PetMediaThumbSafetyTests(TestCase):
    def test_safe_relpath(self):
        self.assertEqual(_safe_media_relpath("animals/dog.jpg"), "animals/dog.jpg")
        self.assertIsNone(_safe_media_relpath("../secret.jpg"))
        self.assertIsNone(_safe_media_relpath("uploads/x.jpg"))


class SmartCropHelpersTests(SimpleTestCase):
    def test_focus_returns_unit_interval(self):
        im = Image.new("RGB", (400, 300), color=(200, 200, 200))
        # dark blob off-center (more edges)
        for y in range(40, 120):
            for x in range(250, 360):
                im.putpixel((x, y), (20, 20, 20))
        fx, fy = estimate_subject_focus(im)
        self.assertGreaterEqual(fx, 0.0)
        self.assertLessEqual(fx, 1.0)
        self.assertGreaterEqual(fy, 0.0)
        self.assertLessEqual(fy, 1.0)
        self.assertGreater(fx, 0.45)  # biased toward right blob

    def test_smart_cover_square(self):
        im = Image.new("RGB", (800, 400), color=(10, 10, 10))
        out = smart_cover_square(im, 0.75, 0.5)
        self.assertEqual(out.size[0], out.size[1])
        self.assertEqual(out.size[0], 400)

    def test_extreme_aspect_winshow_like(self):
        # 204×122 ≈ 1.67 — ca Winshow
        self.assertTrue(is_extreme_aspect(204, 122))
        self.assertFalse(is_extreme_aspect(400, 300))  # 4:3
        self.assertTrue(is_extreme_aspect(100, 200))  # portrait tall

    def test_letterbox_keeps_full_width(self):
        im = Image.new("RGB", (204, 122), color=(30, 90, 40))
        out = letterbox_square(im, fill=(245, 245, 245))
        self.assertEqual(out.size, (204, 204))
        # colțuri = fill (benzi sus/jos)
        self.assertEqual(out.getpixel((0, 0)), (245, 245, 245))
        # mijloc pe banda imaginii = culoarea sursei
        self.assertEqual(out.getpixel((102, 102)), (30, 90, 40))

    def test_square_for_thumb_letterboxes_extreme(self):
        im = Image.new("RGB", (204, 122), color=(50, 50, 50))
        out = square_for_thumb(im)
        self.assertEqual(out.size, (204, 204))


class PetMediaThumbViewTests(TestCase):
    def test_generates_square_smart_thumb(self):
        # 4:3 — smart cover (nu letterbox)
        buf = io.BytesIO()
        Image.new("RGB", (800, 600), color=(120, 80, 40)).save(buf, format="JPEG")
        buf.seek(0)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp)
            rel = Path("animals") / "test_thumb.jpg"
            dest = media / rel
            dest.parent.mkdir(parents=True)
            dest.write_bytes(buf.getvalue())
            with self.settings(MEDIA_ROOT=str(media)):
                request = RequestFactory().get("/img/pet-thumb/400/animals/test_thumb.jpg")
                resp = pet_media_thumb_view(request, size=400, relpath=str(rel).replace("\\", "/"))
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp["Content-Type"], "image/jpeg")
                resp.close()
                thumb_path = media / ".thumbs" / THUMB_VERSION / "400" / "animals__test_thumb.jpg.jpg"
                self.assertTrue(thumb_path.is_file())
                with Image.open(thumb_path) as im:
                    self.assertEqual(im.size[0], im.size[1])
                    self.assertLessEqual(max(im.size), 400)

    def test_extreme_landscape_letterbox_thumb(self):
        buf = io.BytesIO()
        Image.new("RGB", (204, 122), color=(40, 120, 60)).save(buf, format="JPEG")
        buf.seek(0)
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp)
            rel = Path("animals") / "winshow_like.jpg"
            dest = media / rel
            dest.parent.mkdir(parents=True)
            dest.write_bytes(buf.getvalue())
            with self.settings(MEDIA_ROOT=str(media)):
                request = RequestFactory().get("/img/pet-thumb/400/animals/winshow_like.jpg")
                resp = pet_media_thumb_view(request, size=400, relpath=str(rel).replace("\\", "/"))
                self.assertEqual(resp.status_code, 200)
                resp.close()
                thumb_path = media / ".thumbs" / THUMB_VERSION / "400" / "animals__winshow_like.jpg.jpg"
                with Image.open(thumb_path) as im:
                    self.assertEqual(im.size[0], im.size[1])
                    self.assertEqual(im.size[0], 204)  # side = max(orig), apoi ≤400

    def test_unknown_size_404(self):
        with self.settings(MEDIA_ROOT=tempfile.gettempdir()):
            with self.assertRaises(Http404):
                pet_media_thumb_view(
                    None,
                    size=9999,
                    relpath="animals/missing.jpg",
                )
