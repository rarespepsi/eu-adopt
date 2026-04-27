"""
Verificare în masă (carte EU-ADOPT): GET anonim pe rute — fără 500.
Puncte bifate în docs/EU-ADOPT_CARTE_SITE_VERIFICARE.txt când testele trec.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import NoReverseMatch, reverse

from home.models import AnimalListing

User = get_user_model()

# (url_name, get_kwargs dict, querystring)
_CARTE_GET_CASES = [
    ("home", {}, ""),
    ("login", {}, ""),
    ("logout", {}, ""),
    ("forgot_password", {}, ""),
    ("reset_password", {}, ""),  # redirect fără token
    ("signup_choose_type", {}, ""),
    ("signup_pf", {}, ""),
    ("signup_verificare_sms", {}, ""),
    ("signup_retrimite_sms", {}, ""),
    ("signup_pf_sms", {}, ""),
    ("signup_pf_check_email", {}, "?email=test@test.local"),
    ("signup_retrimite_email", {}, ""),
    ("signup_check_activation_status", {}, "?waiting_id=x"),
    ("signup_complete_login", {}, ""),
    ("signup_verify_email", {}, ""),
    ("signup_organizatie", {}, ""),
    ("signup_colaborator", {}, ""),
    ("signup_colaborator", {}, "?tip=transport"),
    ("account", {}, ""),
    ("unified_inbox", {}, ""),
    ("unified_inbox_mark_read", {}, ""),
    ("adoption_bonus_portal", {}, ""),
    ("account_edit_username", {}, ""),
    ("account_upload_avatar", {}, ""),
    ("account_edit", {}, ""),
    ("edit_verificare_sms", {}, ""),
    ("edit_check_email", {}, ""),
    ("edit_verify_email", {}, ""),
    ("admin_analysis_home", {}, ""),
    ("admin_analysis_set_view_as", {}, ""),
    ("admin_analysis_dogs", {}, ""),
    ("admin_analysis_requests", {}, ""),
    ("admin_analysis_users", {}, ""),
    ("admin_analysis_alerts", {}, ""),
    ("reclama_staff", {}, ""),
    ("reclama_pt", {}, ""),
    ("reclama_servicii", {}, ""),
    ("reclama_transport", {}, ""),
    ("reclama_shop", {}, ""),
    ("reclama_mypet", {}, ""),
    ("reclama_magazinul_meu", {}, ""),
    ("reclama_i_love", {}, ""),
    ("reclama_termeni", {}, ""),
    ("reclama_contact", {}, ""),
    ("reclama_mesaje", {}, ""),
    ("reclama_promo_export_summary_now", {"order_id": 1}, ""),
    ("termeni", {}, ""),
    ("termeni_read", {}, ""),
    ("politica_confidentialitate", {}, ""),
    ("politici_altele", {}, ""),
    ("politica_cookie", {}, ""),
    ("politica_servicii_platite", {}, ""),
    ("politica_moderare", {}, ""),
    ("contact", {}, ""),
    ("mypet", {}, ""),
    ("mypet_adopter_adoptions", {}, ""),
    ("magazinul_meu", {}, ""),
    ("transport_operator_panel", {}, ""),
    ("publicitate_harta", {}, ""),
    ("publicitate_checkout_demo", {}, ""),
    ("publicitate_checkout_demo_success", {}, ""),
    ("collab_offers_control", {}, ""),
    ("collab_offer_new", {}, ""),
    ("collab_offer_add", {}, ""),
    ("collab_offer_edit", {"pk": 999999}, ""),
    ("collab_offer_toggle_active", {"pk": 999999}, ""),
    ("collab_offer_delete", {"pk": 999999}, ""),
    ("public_offer_detail", {"pk": 999999}, ""),
    ("public_offer_request", {"pk": 999999}, ""),
    ("mypet_add", {}, ""),
    ("mypet_edit", {"pk": 999999}, ""),
    ("promo_a2_order", {"pk": 999999}, ""),
    ("promo_a2_checkout_demo", {"pk": 999999}, ""),
    ("promo_a2_checkout_demo_success", {"pk": 999999}, ""),
    ("i_love", {}, ""),
    ("wishlist_toggle", {}, ""),
    ("servicii", {}, ""),
    ("transport", {}, ""),
    ("transport_submit", {}, ""),
    ("transport_dispatch_accept", {}, ""),
    ("transport_dispatch_decline", {}, ""),
    ("transport_dispatch_cancel_user", {}, ""),
    ("transport_op_release_job", {}, ""),
    ("transport_op_accept_pending", {}, ""),
    ("transport_op_decline_pending", {}, ""),
    ("transport_dispatch_rate", {"job_id": 999999}, ""),
    ("custi", {}, ""),
    ("shop", {}, ""),
    ("shop_comanda_personalizate", {}, ""),
    ("shop_magazin_foto", {}, ""),
    ("shop_magazin_foto_more", {}, "?offset=0"),
    ("pets_all", {}, ""),
    ("pets_all", {}, "?go=1"),
    ("pets_single", {"pk": 999999}, ""),
    ("pet_track_event", {"pk": 999999}, ""),
    ("pet_send_message", {"pk": 999999}, ""),
    ("pet_adoption_request", {"pk": 999999}, ""),
    ("adoption_bonus_offer_toggle", {}, ""),
    ("adoption_email_owner_action", {}, "?t=x&d=accept"),
    ("mypet_adoption_accept", {"req_id": 999999}, ""),
    ("mypet_adoption_reject", {"req_id": 999999}, ""),
    ("mypet_adoption_extend", {"req_id": 999999}, ""),
    ("mypet_adoption_next", {"req_id": 999999}, ""),
    ("mypet_adoption_finalize", {"req_id": 999999}, ""),
    ("mypet_observatii_update", {"pk": 999999}, ""),
    ("mypet_messages_list", {"pk": 999999}, ""),
    ("mypet_messages_thread", {"pk": 999999, "sender_id": 1}, ""),
    ("mypet_messages_reply", {"pk": 999999, "sender_id": 1}, ""),
    ("adopter_messages_list", {}, ""),
    ("adopter_messages_thread", {"pk": 999999}, ""),
    ("adopter_messages_reply", {"pk": 999999}, ""),
    ("collab_inbox_list", {}, ""),
    ("collab_inbox_thread", {}, ""),
    ("collab_inbox_reply", {}, ""),
    ("collab_client_inbox_list", {}, ""),
    ("collab_client_thread", {}, ""),
    ("collab_client_reply", {}, ""),
    ("collab_contact_message", {}, ""),
]


class CarteBulkNo500Tests(TestCase):
    """Orice GET anonim pe rutele enumerate nu trebuie să returneze 500."""

    def test_anonymous_get_no_server_error(self):
        c = Client()
        failures = []
        for name, kwargs, qs in _CARTE_GET_CASES:
            try:
                path = reverse(name, kwargs=kwargs if kwargs else None)
            except NoReverseMatch as e:
                failures.append(f"{name} {kwargs}: NoReverseMatch {e}")
                continue
            url = path + (qs or "")
            try:
                r = c.get(url)
            except Exception as e:
                failures.append(f"{name} GET {url}: EXC {type(e).__name__}: {e}")
                continue
            if r.status_code >= 500:
                failures.append(f"{name} GET {url}: {r.status_code}")
        self.assertFalse(
            failures,
            "Rute cu 500 sau excepție:\n" + "\n".join(failures),
        )


class CartePetsGoRedirectTests(TestCase):
    """Punct 35: /pets/?go=<id> — redirect (nu 500)."""

    def test_pets_go_redirects_or_404_no_500(self):
        r = Client().get(reverse("pets_all"), {"go": "999999"})
        self.assertLess(r.status_code, 500)
        self.assertIn(r.status_code, (302, 301, 303, 307, 308, 404))


class CartePetsSinglePublishedTests(TestCase):
    """Fișă publică cu animal publicat — GET 200."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="carte_pet_owner",
            email="carte_pet_owner@test.local",
            password="CartePetPass123",
        )
        self.listing = AnimalListing.objects.create(
            owner=self.owner,
            name="CarteTest",
            species="dog",
            is_published=True,
        )

    def test_pets_single_published_200(self):
        r = Client().get(reverse("pets_single", args=[self.listing.pk]))
        self.assertEqual(r.status_code, 200)
