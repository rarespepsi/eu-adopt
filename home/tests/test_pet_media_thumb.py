from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.http import Http404
from PIL import Image
import io
import tempfile
from pathlib import Path

from home.pet_media_thumb import _safe_media_relpath, pet_media_thumb_view


class PetMediaThumbSafetyTests(TestCase):
    def test_safe_relpath(self):
        self.assertEqual(_safe_media_relpath("animals/dog.jpg"), "animals/dog.jpg")
        self.assertIsNone(_safe_media_relpath("../secret.jpg"))
        self.assertIsNone(_safe_media_relpath("uploads/x.jpg"))


class PetMediaThumbViewTests(TestCase):
    def test_generates_and_serves_thumb(self):
        buf = io.BytesIO()
        Image.new("RGB", (2000, 1500), color=(120, 80, 40)).save(buf, format="JPEG")
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
                thumb_path = media / ".thumbs" / "400" / "animals__test_thumb.jpg.jpg"
                self.assertTrue(thumb_path.is_file())
                with Image.open(thumb_path) as im:
                    self.assertLessEqual(max(im.size), 400)

    def test_unknown_size_404(self):
        with self.settings(MEDIA_ROOT=tempfile.gettempdir()):
            with self.assertRaises(Http404):
                pet_media_thumb_view(
                    None,
                    size=9999,
                    relpath="animals/missing.jpg",
                )
