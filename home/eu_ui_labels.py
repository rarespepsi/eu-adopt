"""
UI page strings for EU sites — multi-language packs (variant B).
Romanian stays hard-coded on .ro templates via eu_t / if eu_site_active fallback.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.utils.translation import get_language

EU_UI_DEFAULT_LANGUAGE = "en"
EU_UI_HUB_LANGUAGE_CODES = frozenset({"en", "de", "fr", "es", "it", "pl", "nl", "pt", "ro"})

_I18N_JSON = Path(__file__).resolve().parent / "eu_ui_labels_i18n.json"
_EN: dict[str, str] = {
    # Common / chrome
    "messages_new": "New messages: {n}",
    "messages_none": "No new messages",
    "messages_title_new": "New messages: {n}",
    "messages_title_none": "No new messages",
    "loading": "Loading…",
    "save": "Save",
    "cancel": "Cancel",
    "close": "Close",
    "send": "Send",
    "search": "Search",
    "back": "Back",
    "next": "Next",
    "yes": "Yes",
    "no": "No",
    "error": "Something went wrong. Please try again.",
    "required": "Required",
    "email": "Email",
    "policy": "Policy",
    "response_time": "Response time",
    "working_days": "1–3 working days",
    "in_progress": "to be completed",
    # Login / Intra
    "login_title": "Sign in – EU-ADOPT",
    "login_heading": "Sign in",
    "login_sub": "Simple sign-in to manage your listings and preferences.",
    "login_user": "Email / username",
    "login_user_ph": "email or username",
    "login_password": "Password",
    "login_show_pass": "Show password",
    "login_submit": "Sign in",
    "login_forgot": "Forgot your password?",
    "login_no_account": "No account yet?",
    "login_create": "Create account",
    "login_failed": "Sign-in failed.",
    "login_reset_ok": "Password was reset.",
    "login_reset_ok_hint": "Sign in with your new password.",
    "login_aria": "EU-ADOPT sign-in",
    "login_pre_slogan": "EU-Adopt — Don't buy!!! Free adoption site!",
    # Contact
    "contact_title": "Contact | EU-ADOPT",
    "contact_heading": "Contact EU-ADOPT",
    "contact_intro": "Choose the right channel and email us. We usually reply within 1–3 working days.",
    "contact_emails_h": "EU-Adopt email addresses",
    "contact_emails_lead": "Tap Send email — your mail app opens with the recipient filled in.",
    "contact_send_email": "Send email",
    "contact_emails_note": "All messages are handled by the EU-Adopt team. For animal medical emergencies, contact a vet immediately.",
    "contact_aria": "Contact page",
    "contact_legal_h": "Platform operator details",
    "contact_legal_name": "Legal name:",
    "contact_legal_cui": "Company ID:",
    "contact_legal_hq": "Registered office:",
    "contact_legal_phone": "Phone:",
    "contact_legal_email": "General email:",
    "contact_whatsapp": "WhatsApp",
    "contact_call": "Call",
    "contact_prefer_whatsapp": "Prefer WhatsApp message (recommended outside Romania).",
    "contact_card1_h": "1) General support",
    "contact_card1_p": "Account, sign-in, using the pages and technical issues.",
    "contact_card2_h": "2) Personal data (GDPR)",
    "contact_card2_p": "Access, rectification, erasure, restriction, portability, objection.",
    "contact_card2_pol": "Privacy",
    "contact_card3_h": "3) Advertising and paid services",
    "contact_card3_p": "Promotion, campaigns, slots and paid appearances.",
    "contact_card3_pol": "Paid services",
    "contact_card4_h": "4) Moderation and reports",
    "contact_card4_p": "Suspect content, abusive accounts, fraud or rule breaches.",
    "contact_card4_pol": "Moderation",
    # Terms hub
    "terms_title": "Terms | EU-ADOPT",
    "terms_heading": "Legal documents – EU-ADOPT",
    "terms_intro": "Choose the document you want to read.",
    "terms_cat1": "1) Terms and conditions",
    "terms_cat1_sub": "General rules of use",
    "terms_cat2": "2) Privacy policy",
    "terms_cat2_sub": "Protection of personal data",
    "terms_cat3": "3) Additional policies",
    "terms_cat3_sub": "Cookies, paid services and moderation",
    "terms_aria": "Legal documents hub",
    "terms_en_note": "Full legal text is currently in Romanian. An English version is being prepared; the Romanian documents remain the legally binding version.",
    # 404
    "err404_title": "Page not found | EU-Adopt",
    "err404_h1": "This page does not exist",
    "err404_body": "The address was not found or has been moved.",
    "err404_home": "Back to home",
    # Home
    "home_title": "EU Adopt – Home",
    "home_meta": "EU-ADOPT Home – dog and cat adoption across Europe, listings and pet services.",
    "home_mission_adopted": "In our care: {n} adopted",
    "home_mission_looking": "pets looking for a home right now",
    "home_mission_cta": "Be part of the journey →",
    "home_mission_cta_title": "Support the project — donations",
    "home_welcome_title": "Welcome to EU-Adopt",
    "home_welcome_p1": "Animals are not bought or sold here. Together, we help them find a home and someone who will love them.",
    "home_welcome_p2": "On EU-Adopt you can:",
    "home_welcome_li1": "discover animals from NGOs and shelters waiting for a family;",
    "home_welcome_li2": "support NGOs by buying a photo or styled item in the Shop — your contribution goes to them;",
    "home_welcome_li3": "receive small benefits for every confirmed adoption, as a thank-you;",
    "home_welcome_li4": "share animals on social media and increase both their chance of a home and your chance of monthly prizes.",
    "home_welcome_p3": "Every visit and every share can change an animal’s story. Thank you for being here.",
    "home_welcome_close_hint": "(Close this note and continue on EU-Adopt.)",
    "home_welcome_close_btn": "Close",
    "home_a2_aria": "12 dogs available for adoption",
    "home_pub_aria_top": "Sponsored listings – top",
    "home_pub_aria_bottom": "Sponsored listings – bottom",
    "home_burtiera_aria": "EU-Adopt notice",
    "home_burtiera_default": "#EuAdopt #DontBuy – EU-Adopt is an independent initiative promoting animal adoption. This project is not affiliated with, funded by, or run by the European Union.",
    "home_note_share": "Share EU-Adopt, support a transport or a crate, buy a photo from the photo shop or promote a listing for visibility – never buying or selling animals on the site.",
    "home_note_share_guest": "Share EU-Adopt, support a transport or a crate, or buy a photo from the photo shop – never buying or selling animals on the site.",
    "home_cta_support": "Support EU-Adopt",
    "home_cta_pets": "Come meet us!",
    "home_cta_pets_title": "See your friends",
    "home_note_close": "Close note",
    "home_note_title": "Quick guide – EU-Adopt pages",
    "home_note_rule": "Important rule: animals are not bought or sold on this site. Adoption happens by request and agreement with the keeper or NGO — not through commercial transactions on the platform.",
    "home_note_home_h": "Home",
    "home_note_home_p": "Overview, adoption listings grid and quick access to other sections.",
    "home_note_pt_h": "Find a friend",
    "home_note_pt_p_auth": "List of available animals; filters; open a profile for details, messages and adoption request. The heart saves the animal in I Love.",
    "home_note_pt_p_guest": "List of available animals; filters; open a profile for details, messages and adoption request. After you sign in, you can use the heart to save animals on the I Love page.",
    "home_note_ficha_h": "Animal profile (subpage)",
    "home_note_ficha_p": "Animal details, messages to the keeper, adoption flow. Promoting in the A2 grid is paid visibility for the listing — it does not mean buying the animal.",
    "home_note_svc_h": "Services",
    "home_note_svc_p": "Partner services (e.g. clinic, training) related to animal care — not trade in animals.",
    "home_note_tr_h": "Transport",
    "home_note_tr_p": "Logistics support for adoptions and donations (e.g. crates). Always outside any animal sale.",
    "home_note_crates_h": "Crates",
    "home_note_crates_p": "Info and involvement for donating transport crates — unrelated to selling animals.",
    "home_note_shop_h": "Shop",
    "home_note_shop_p": "Products and materials; proceeds support the cause. There is no “price for an animal” here.",
    "home_note_shop_pers_h": "Shop → Custom orders",
    "home_note_shop_pers_p": "Custom design orders (e.g. T-shirts); money goes to the project, not to buying an animal.",
    "home_note_shop_photo_h": "Shop → Photo shop (“buy a photo”)",
    "home_note_shop_photo_p": "You buy a photo/support licence; the amount goes toward NGOs — financial support, not buying an animal.",
    "home_note_mypet_h": "MyPet",
    "home_note_mypet_p": "Your panel if you have an account: own listings, messages, adoptions in progress. Promoting a listing = visibility, not a sale.",
    "home_note_ilove_h": "I Love",
    "home_note_ilove_p": "Animals you marked with a heart, so you can return to them easily.",
    "home_note_pub_h": "Advertising",
    "home_note_pub_p": "Book advertising spaces (e.g. on PDF materials) for your brand or organisation — not for selling animals.",
    "home_note_mag_h": "My shop",
    "home_note_mag_p": "Area for collaborator partners: offers and settings for the partner account.",
    "home_note_account_h": "Account, signup, legal",
    "home_note_account_p_auth": "My account, signup, Contact, Terms and footer policies — for rights, privacy and rules of use.",
    "home_note_account_p_guest": "Sign in, signup, Contact, Terms and footer policies — for rights, privacy and rules of use.",
    "home_note_cta_title": "Help too!",
    "home_note_cta_aria": "Get involved",
    "prelaunch_hint_title": "Pre-launch tip",
    "prelaunch_hint_close": "Close",
    "prelaunch_hint_ok": "Got it",
    "prelaunch_hint_mypet": "MyPet: add published animals, then you can promote one dog on Home for free (1 promotion per account).",
    "prelaunch_hint_publicitate_harta": "Advertising: pick a slot on the map, add it to the cart and activate it for free (1 slot per account during pre-launch).",
    "prelaunch_hint_publicitate_cos": "Advertising cart: move to the general Cart → Pay → free activation.",
    "prelaunch_hint_collab_offers": "Partner offers: publish services/products from My shop; no number cap.",
    "prelaunch_hint_pets_all": "Find a friend: browse listings; from a profile you can promote an animal on the Home grid.",
    "prelaunch_hint_i_love_cos": "Cart: during pre-launch you can only complete advertising or Home-grid promotion (free).",
    "prelaunch_banner_label": "Pre-launch",
    "prelaunch_banner_body": "Shop, donations and commercial payments are temporarily closed. Advertising and Home-grid promotion are free so you can learn the platform.",
    "prelaunch_msg_shop": "The Shop (products, photo shop, custom items including coach/crates) opens after launch. You can use free advertising and partner signup now.",
    "prelaunch_msg_donatii": "Donations and online tax forms activate after launch. During pre-launch we focus on populating the platform.",
    "prelaunch_msg_custi": "The crates / coach page is temporarily closed during pre-launch. Please come back after the official launch.",
    "prelaunch_msg_checkout": "The cart contains commercial items (shop, paid services) that cannot be completed during pre-launch. Remove them or wait for launch.",
    "prelaunch_msg_cart_add": "You cannot add this item to the cart during pre-launch. The Shop and paid offers open after launch.",
    "prelaunch_msg_adopt": "The “I want to adopt” button is inactive during the population period. Online adoptions open after the official launch.",
    "pub_nudge_label": "INFO",
    "pub_nudge_text": "During the population period, advertising slots are free.",
    "pub_nudge_later": "Later",
    "pub_nudge_cta": "Get a free slot now",
    "prelaunch_disc_title": "PRE-LAUNCH period.",
    "prelaunch_disc_body": "The EU-Adopt platform is preparing for the official launch. Access is allowed only for users with an existing account. Public registration is temporarily disabled; new accounts are created only by team invitation.",
    "checkout_prelaunch_free": "Pre-launch stage: activation is free — no payment is required.",
    "login_pre_left_aria": "PRE-LAUNCH information — introduction",
    "login_pre_badge": "PRE-LAUNCH period",
    "login_pre_p1": "EU-Adopt is a platform dedicated to responsible adoptions and cooperation between shelters, associations, veterinary clinics, shops, transporters and other animal-care services.",
    "login_pre_p2": "The project is supported by professional associations and people involved in this field. Its goal is a single meeting point between animals looking for a family, the organisations that care for them, and people who want to adopt or help.",
    "login_pre_p3": "The platform is currently in a population, validation and testing stage before the official public launch.",
    "login_pre_emph": "Access is currently available only to registered users and collaborators.",
    "login_pre_right_aria": "PRE-LAUNCH information — current stage",
    "login_pre_heading": "During this period:",
    "login_pre_li1": "collaborator accounts are being validated;",
    "login_pre_li2": "animals available for adoption are being added;",
    "login_pre_li3": "platform services and partners are being configured;",
    "login_pre_li4": "final functional and security tests are being carried out.",
    "login_pre_max": "For the population stage we recommend adding initially a maximum of 5 animals and a single representative service or product, as applicable. After the official launch, information can be completed and updated at any time.",
    "login_pre_report": "Please report any error, blockage, incorrectly displayed information or technical issue you encounter while using the platform. Your comments and suggestions help us improve it before the public launch.",
    "login_pre_launch": "The public launch will take place after the population and information-validation process is complete.",
    "login_pre_thanks": "Thank you for your interest, trust and support.",
    "login_pre_team": "The EU-Adopt team",
    "onboard_skip": "Skip",
    "onboard_tour": "Continue the tour",
    "onboard_close": "Close",
    "onboard_next": "Next",
    "onboard_done": "Got it",
    "onboard_tour_aria": "Page tour",
    "onboard_guide_hint": "Questions? Tap the EU-Adopt Guide button at the bottom right.",
    "onboard_home_title": "Welcome to Home",
    "onboard_home_text": "EU-Adopt’s main page: see promoted animals, use the menu, and come back here any time after login.",
    "onboard_home_s1": "Area A1 — the site’s title and main message.",
    "onboard_home_s2": "Grid A2 — listings promoted for adoption (Priority 2).",
    "onboard_home_s3": "Top menu — Find a friend, Services, MyPet, Advertising and the other sections.",
    "onboard_mypet_title": "MyPet — your panel",
    "onboard_mypet_text": "Here you publish animals, see messages and manage adoption requests. Complete each animal’s profile as fully as possible.",
    "onboard_mypet_s1": "Add a pet — create a new listing (photos, details, publish).",
    "onboard_mypet_s2": "Active / Adopted — switch the list between current and adopted animals.",
    "onboard_mypet_s3": "Species filters — Dogs, Cats, Other.",
    "onboard_mypet_s4": "Animal list — click a row for the profile, messages or actions.",
    "onboard_publicitate_harta_title": "Advertising — rate map",
    "onboard_publicitate_harta_text": "Pick a slot on the map, see details on the left and add it to the cart. During pre-launch, advertising may be free (limit per account).",
    "onboard_publicitate_harta_s1": "Section tabs — HOME, Find a friend, I Love etc. (rates per page).",
    "onboard_publicitate_harta_s2": "Map — tap a free slot to select it.",
    "onboard_publicitate_harta_s3": "Slot details — period, price and Add to cart.",
    "onboard_publicitate_harta_s4": "Advertising cart — complete the order after you add slots.",
    "onboard_pets_all_title": "Find a friend — animals for adoption",
    "onboard_pets_all_text": "Browse listings published by shelters and associations. Filter by preference and open an animal profile for details.",
    "onboard_pets_all_s1": "Top strip — messages and news from the platform.",
    "onboard_pets_all_s2": "Filters and actions — Find my match, Filters (county, age, size), Help a soul.",
    "onboard_pets_all_s3": "Animal grid — click a card for the profile; the heart saves it in I Love.",
    "onboard_pets_all_s4": "Navbar menu — quick access to MyPet, Services, Transport etc.",
    "onboard_servicii_title": "Services — EU-Adopt partners",
    "onboard_servicii_text": "Find veterinary clinics, shops and salons. Filter by county/city and species, then open an offer.",
    "onboard_servicii_s1": "Geo filters — County and City/Place; Reset clears the selection.",
    "onboard_servicii_s2": "Tabs: Clinics, Shops, Salons — offer categories.",
    "onboard_servicii_s3": "Offer grid — click the image or card for details and the I Love cart.",
    "onboard_servicii_s4": "S1 strip — partner promotions and information.",
    "onboard_i_love_title": "I Love — your favourites",
    "onboard_i_love_text": "Animals marked with a heart appear here. You can return to the profile, send messages or promote a listing.",
    "onboard_i_love_s1": "Page title — the list of animals saved with a heart.",
    "onboard_i_love_s2": "Animal cards — click for the profile; the envelope opens messages.",
    "onboard_i_love_s3": "Left advertising boxes — partner promotions (if active).",
    "onboard_transport_title": "Transport — moving animals",
    "onboard_transport_text": "A transport request for adoption or other trips. You fill in places, date and details; transporters reply on the platform.",
    "onboard_transport_s1": "Request form — departure, destination, date, animal details.",
    "onboard_transport_s2": "Information and status — follow your request or transporter offers.",
    "onboard_transport_s3": "Auxiliary areas — useful links, crate/coach donations (when active).",
    "onboard_shop_title": "EU-Adopt Shop",
    "onboard_shop_text": "Products for animals: dogs, cats, accessories. You can also open the NGO photo shop or donations from the top strip.",
    "onboard_shop_s1": "SH1 strip — NGO Photo Shop and the Help a soul donations link.",
    "onboard_shop_s2": "Species tabs — Dogs, Cats, Accessories.",
    "onboard_shop_s3": "Products — click a card for details and cart (after launch).",
    "onboard_publicitate_cos_title": "Advertising cart",
    "onboard_publicitate_cos_text": "Check the chosen slots and periods, then go to payment / activation. During pre-launch activation may be free.",
    "onboard_publicitate_cos_s1": "Change the map section (HOME, PT, I Love…) for other slots.",
    "onboard_publicitate_cos_s2": "Selected slot summary — change the period or quantity.",
    "onboard_publicitate_cos_s3": "Navigation — back to the rate map or my orders.",
    "onboard_collab_offers_control_title": "My shop — offers",
    "onboard_collab_offers_control_text": "Collaborator panel: publish and manage offers/services/products.",
    "onboard_collab_offers_control_s1": "Add offer — new form (photos, price, validity).",
    "onboard_collab_offers_control_s2": "List filters — search by title or offer status.",
    "onboard_collab_offers_control_s3": "Offers table — activate/deactivate, edit or delete.",
    "onboard_collab_offers_control_s4": "Messages — “I want this offer” requests from users.",
    "onboard_pets_single_title": "Animal profile",
    "onboard_pets_single_text": "Full details: photos, traits, messages to the shelter. From the profile you can request adoption (when active) or save with the heart.",
    "onboard_pets_single_s1": "Profile title — the animal’s name and quick identification.",
    "onboard_pets_single_s2": "Photo/video gallery — click an image to enlarge (pinch on mobile).",
    "onboard_pets_single_s3": "Adoption — request button (if active); otherwise see the listing status.",
    "onboard_pets_single_s4": "Back to list — return to Find a friend or the previous page.",
    "onboard_i_love_cos_title": "I Love / general cart",
    "onboard_i_love_cos_text": "The cart brings together Services offers and advertising. During pre-launch you complete only free items (ads / promotion).",
    "onboard_i_love_cos_s1": "Site menu — return to the pages where you added products.",
    "onboard_i_love_cos_s2": "Cart content — check the lines and go to payment when available.",
    "home_promo_pill": "Promotion",
    # PT
    "pt_title": "Find a friend | EU-ADOPT",
    "pt_meta": "Find a friend – animals for adoption on EU-ADOPT. Filter by preference, open profiles and contact for adoption.",
    "pt_filters": "Filters",
    "pt_filters_dogs": "Dog filters",
    "pt_filters_cats": "Cat filters",
    "pt_filters_other": "Other filters",
    "pt_find_match": "Find my match",
    "pt_find_match_title": "Find your matching soul",
    "pt_help_soul": "Help a soul!",
    "pt_help_soul_title": "Support EU-ADOPT",
    "pt_reset": "Reset filters",
    "pt_search_title": "Find your friend",
    "pt_all": "All",
    "pt_dogs": "Dogs",
    "pt_cats": "Cats",
    "pt_other": "Other",
    "pt_county": "County",
    "pt_country": "Country",
    "pt_region": "Region / county",
    "pt_size": "Size",
    "pt_age": "Age",
    "pt_sex": "Sex",
    "pt_all_opt": "— All —",
    "pt_size_s": "Small",
    "pt_size_m": "Medium",
    "pt_size_l": "Large",
    "pt_sex_m": "MALE",
    "pt_sex_f": "FEMALE",
    "pt_open_filters": "Open filters",
    "pt_collapse_filters": "Collapse filters",
    "pt_ask_about": "Ask about me?",
    "pt_list_aria": "Animal list",
    "pt_see_profile": "View profile {name}",
    "pt_ads_aria": "Ads",
    # Transport
    "transport_title": "Transport | EU-ADOPT",
    "transport_request": "Transport request",
    "transport_submit": "SUBMIT REQUEST",
    "transport_aria": "Transport content",
    "transport_t1_title": "Vet transport – request",
    "transport_t1_intro": (
        "Your request goes to our transport team (transport@eu-adopt.ro). "
        "If we find a suitable transport option, we will inform you. "
        "If not, arrangements remain between the adopter and the shelter."
    ),
    "transport_submit_ok": (
        "Your transport request was sent to our team. "
        "If we find transport, we will contact you; otherwise it remains with the adopter and the shelter."
    ),
    "transport_want": "I want transport",
    "transport_donate": "Donate to a cause",
    "transport_collapse": "Collapse form",
    "transport_actions_aria": "Transport actions",
    "transport_today": "Transport today",
    "transport_intl": "International transport",
    "transport_intl_tip": "Safe pet transport in-country and across borders, with a dedicated vehicle.",
    "transport_county": "COUNTY",
    "transport_country": "DESTINATION COUNTRY",
    "transport_city": "CITY / PLACE",
    "transport_from": "PICK-UP POINT",
    "transport_to": "DROP-OFF POINT",
    "transport_ph_country": "Where the animals are going",
    "transport_country_hint": "Origin is Romania. Choose the destination country for this transport.",
    "transport_ph_county": "Choose or type the county",
    "transport_ph_city": "Choose the county first",
    "transport_ph_from": "Locality, address or pick-up point",
    "transport_ph_to": "Locality, address or drop-off point",
    "transport_map_pick": "Pick on map",
    "transport_map_pick_title": "Open the map and choose the location",
    "transport_datetime": "DATE AND TIME",
    "transport_cal": "Open calendar",
    "transport_dogs_n": "NO. OF DOGS",
    "transport_route": "ROUTE",
    "transport_route_nat": "National",
    "transport_route_int": "International",
    "transport_urgency": "URGENCY",
    "transport_urg_flex": "No strict deadline",
    "transport_urg_today": "Transport today",
    "transport_urg_24": "24 hours",
    "transport_expand_hub": "Show facilities",
    "transport_collapse_hub": "Hide facilities",
    "transport_t2_1": "International transport",
    "transport_t2_1_tip": "Safe pet transport in-country and across borders, with a dedicated vehicle.",
    "transport_t2_2": "Interior facilities",
    "transport_t2_2_tip": "60 specially fitted places for safe transport.",
    "transport_t2_3": "Ventilation / heat",
    "transport_t2_3_tip": "Air conditioning and heating for a steady temperature on the road.",
    "transport_t2_4": "GPS tracking",
    "transport_t2_4_tip": "Real-time tracking of the route and vehicle location.",
    "transport_t2_5": "VET · Vet assistance",
    "transport_t2_5_tip": "Vet on board or veterinary assistance on request during transport.",
    "transport_t2_6": "Food stops",
    "transport_t2_6_tip": "Regular stops for water, food and rest along the route.",
    "transport_t2_7": "Individual comfort",
    "transport_t2_7_tip": "Each animal has its own crate for safety and calm.",
    "transport_t2_8": "Medical VET",
    "transport_t2_8_tip": "Veterinary equipment and treatment available during the journey.",
    "transport_t2_9": "Grooming VET",
    "transport_t2_9_tip": "Grooming and veterinary care on request during road breaks.",
    "transport_center_crates_title": "Coach crate map — view crate places",
    "transport_center_crates_alt": "EU-Adopt coach — crate map",
    "transport_bulina_partner_title": "Suflet și Caracter — We Come To You",
    "transport_bulina_ring": "* Help a cause * Soul * Character * We Come To You *",
    # /custi/
    "custi_title": "Coach crate map | EU-Adopt",
    "custi_aria": "Coach crate map",
    "custi_h1": "EU-ADOPT coach — Sponsor a crate",
    "custi_sub": "Each place gives safety and care to a soul on the way home. Pick a crate and help us complete the project!",
    "custi_back_transport": "Back to Transport",
    "custi_back_pets": "Back to Your Friend",
    "custi_donate_medical": "Donate for medical care and food",
    "custi_cages_aria": "Numbered crates: 1–30 left, 31–60 right",
    "custi_bottom": "Help build the project · We COME TO YOU · Choose a crate and sponsor it!",
    "custi_close": "Close",
    "custi_h2_general": "Donation for medical care and food",
    "custi_h2_slot": "Donation for place",
    "custi_val_crate": "Crate value",
    "custi_val_left": "Amount left",
    "custi_currency": "RON",
    "custi_sum_label": "Amount to donate",
    "custi_other_sum": "Other amount",
    "custi_donate_btn": "Donate",
    "custi_thanks": "Thank you",
    "custi_alert_min": "Choose or enter an amount of at least 25 RON.",
    # /donatii/
    "don_title": "Donations | EU-ADOPT",
    "don_aria": "EU-ADOPT donations",
    "don_back_transport": "← Back to Transport",
    "don_summary_h": "Request summary",
    "don_summary_source": "Source:",
    "don_summary_type": "Type:",
    "don_summary_loc": "Crate place:",
    "don_summary_suma": "Proposed amount (RON):",
    "don_h1": "Donations — support the project",
    "don_lead": "Thank you for wanting to help. You can use a bank transfer, Form 230 (3.5%), and the company sponsorship contract — together with our partner for the animal cause. PDFs are generated on the site; the IBAN shown stays provisional until the partner account is fully activated.",
    "don_partner_aria": "Partner for the animal cause",
    "don_partner_legal": "Association for animal protection",
    "don_partner_badge": "Partner donation account — activation in progress",
    "don_partner_blurb": "Asociația Suflet și Caracter is our designated partner for animal causes on this page. The IBAN and full details for donations directly to the association will appear after final activation.",
    "don_pillars_aria": "What we support",
    "don_pillar_1": "Love and empathy for animals",
    "don_pillar_2": "Support, protection and safety",
    "don_pillar_3": "Souls cared for with care",
    "don_pillar_4": "Responsibility and character",
    "don_sms_h": "Donate by SMS",
    "don_sms_p": "Here we will describe SMS donation options: short code (when active), message text, price per SMS, legal terms and completion systems (e.g. confirmation, billing, reporting to the operator). Until the service is contracted, information stays provisional.",
    "don_sms_li1": "Activate short code and keyword with an authorised operator / aggregator.",
    "don_sms_li2": "Clear user instructions (what to send, cost, how to stop).",
    "don_sms_li3": "Later panel integration (if needed) for SMS payment reconciliation.",
    "don_options_aria": "Donation options",
    "don_quick_h": "For a noble cause",
    "don_quick_p": "Pick a guide amount; continue with a bank transfer (IBAN in the next box) and note EU-ADOPT donation in the payment details.",
    "don_amounts_aria": "Amounts in RON",
    "don_amt_25": "25 RON",
    "don_amt_50": "50 RON",
    "don_amt_100": "100 RON",
    "don_other_ph": "Other amount",
    "don_apply": "Apply",
    "don_bank_h": "Bank transfer",
    "don_iban_label": "IBAN (provisional)",
    "don_copy_iban": "Copy IBAN",
    "don_copied": "Copied!",
    "don_f230_h": "Form 230 (3.5%)",
    "don_f230_p": "PDF with your details and the beneficiary from site settings. It does not send automatically to ANAF.",
    "don_f230_btn": "Generate form",
    "don_sponsor_h": "Company sponsorship",
    "don_sponsor_p": "Model PDF contract for a legal entity (company details + provisional beneficiary).",
    "don_sponsor_btn": "Generate contract",
    "don_info": "Important: PDF documents are indicative; check with a tax or legal specialist before filing or signing. The IBAN in “Bank transfer” is being aligned to the partner account",
    "don_info_contact": "For questions:",
    "don_values_h": "Every contribution counts",
    "don_v_trust": "Trust",
    "don_v_compassion": "Compassion",
    "don_v_respect": "Respect",
    "don_v_community": "Community",
    "don_slogan": "Be the voice of those who cannot speak.",
    "don_nav_aria": "Quick links",
    "don_nav_crates": "Coach crate map",
    "don_nav_transport": "Transport page",
    "don_nav_account": "Complete my details",
    "don_nav_login": "Sign in (autofill)",
    "transport_t3_title": "For transport…",
    "transport_t3_aria": "Transport advertising spaces",
    "transport_map_title": "Choose location on the map",
    "transport_map_hint": "Search below or tap the map to place a pin. You can move the pin.",
    "transport_map_search": "Search address",
    "transport_map_search_ph": "Search address, street, locality…",
    "transport_map_cancel": "Cancel",
    "transport_map_ok": "Use this location",
    "transport_adopt_h": "Adoption steps",
    "transport_adopt_p": "Fill in the transport details below. Then tap “Continue adoption request” to return to the profile and send the request to the organisation.",
    "transport_adopt_a": "Continue adoption request",
    # Pet profile
    "pet_back": "BACK TO LIST",
    "pet_share": "SHARE",
    "pet_share_aria": "Share (copy profile link)",
    "pet_title_prefix": "PET PROFILE",
    "pet_promote": "PROMOTE ME",
    "pet_promote_aria": "Promote me",
    "pet_msg_ph": "Write your message to the NGO / owner…",
    "pet_adopt_title": "Adoption request",
    "pet_adopt_msg": "Message (optional)",
    "pet_adopt_msg_ph": "Why do you want to adopt? Do you have a yard, other pets…",
    "pet_adopt_cancel": "Cancel",
    "pet_adopt_send": "Send request",
    "pet_adopt_how": "How will you pick up the animal?",
    "pet_adopt_finish": "Finish adoption request",
    "pet_adopt_close": "Close",
    "pet_adopt_send_full": "Send adoption request",
    "pet_adopt_continue": "Continue",
    "pet_adopt_qr_aria": "Adoption and QR code",
    "pet_link_copied": "Link copied. You can paste it to share.",
    "pet_link_copy_fail": "Could not copy the link.",
    "pet_meta_title": "{name} – Adoption | EU-ADOPT",
    "pet_meta_fallback": "Profile {name} – adoption via EU-ADOPT. Details, location and message to the owner on the platform.",
    "pet_lbl_name": "PET NAME *",
    "pet_lbl_species": "SPECIES",
    "pet_lbl_age": "APPROX. AGE *",
    "pet_lbl_size": "SIZE *",
    "pet_lbl_color": "COLOUR",
    "pet_lbl_sterilized": "NEUTERED / SPAYED",
    "pet_lbl_vaccinated": "VACCINATED",
    "pet_lbl_health_book": "HEALTH BOOKLET",
    "pet_lbl_chip": "CHIP",
    "pet_lbl_chip_rua": "CHIP / RUA",
    "pet_lbl_sex": "SEX",
    "pet_lbl_weight": "WEIGHT (APPROX.)",
    "pet_lbl_county": "COUNTY",
    "pet_lbl_country": "COUNTRY",
    "pet_lbl_region": "REGION / COUNTY",
    "pet_lbl_city": "CITY / PLACE",
    "pet_lbl_medical": "MEDICAL ISSUES",
    "pet_lbl_story": "WHO I AM AND WHERE I'M FROM",
    "pet_lbl_messages": "MESSAGES",
    "pet_species_dog": "Dog",
    "pet_species_cat": "Cat",
    "pet_species_other": "Other animal",
    "pet_choose": "Choose",
    "pet_sex_m": "MALE",
    "pet_sex_f": "FEMALE",
    "pet_msg_own": "This is your listing.",
    "pet_msg_login": "Sign in to send a message.",
    "pet_want_adopt": "I WANT TO ADOPT",
    "pet_traits_h": "Personality",
    "pet_traits_match_h": "Adopter match details",
    "pet_observatii_h": "Notes (details about the animal)",
    "pet_observatii_hint": "Behaviour, care — visible to adopters.",
    "pet_qr_title": "Scan the profile",
    "pet_qr_hint": "Open on your phone",
    "pet_qr_aria": "Profile QR code",
    "pet_qr_alt": "QR code to this profile",
    "pet_adopt_demo_note": "Demo only",
    "pet_adopt_inactive_note": "Inactive during population phase",
    "pet_adopt_state_aria": "Adoption status",
    "pet_adopt_state_free": "Available",
    "pet_adopt_demo_msg": "This animal is for demonstration (DEMO) and cannot be adopted.",
    "pet_adopt_inactive_msg": (
        "The “I want to adopt” button is inactive during the population phase. "
        "Online adoptions open after the official launch."
    ),
    "pet_adopt_intro": (
        "Fill in the form. Your details will be sent to the owner / shelter, who will contact you directly."
    ),
    "pet_adopt_lbl_last": "Last name *",
    "pet_adopt_lbl_first": "First name *",
    "pet_adopt_lbl_email": "Email *",
    "pet_adopt_lbl_phone": "Phone *",
    "pet_adopt_lbl_phone_prefix": "Phone prefix",
    "pet_adopt_lbl_county": "County *",
    "pet_adopt_lbl_city": "City *",
    "pet_adopt_accept_terms": "I accept the Terms and conditions *",
    "pet_adopt_accept_gdpr": "I accept the Privacy policy (GDPR) *",
    "pet_adopt_after_transport": (
        "You completed the veterinary transport step. You can now send the request to the organisation."
    ),
    "pet_adopt_choose_hint": "Choose an option before sending the adoption request.",
    "pet_adopt_pickup_personal": "Personal pickup (I meet the organisation / agreed location)",
    "pet_adopt_pickup_transport": (
        "I want veterinary transport (fill the form, then return to the adoption request)"
    ),
    "pet_adopt_transport_need_county": (
        "For the transport option, complete your county in your account, then return to this profile."
    ),
    "pet_share_title_named": "{name}'s profile | EU-Adopt",
    "pet_share_title": "Animal profile | EU-Adopt",
    "pet_share_text": "Check out this profile on EU-Adopt:",
    "pet_link_copied_mobile": (
        "Profile link copied. Open the app where you want to send it (WhatsApp, Messages, etc.) "
        "and paste (long-press → Paste)."
    ),
    "pet_link_copied_desk": (
        "Profile link copied. Paste with Ctrl+V in a message, email, or wherever you want to share it."
    ),
    "pet_link_fail_mobile": (
        "Could not copy the link automatically. Use the QR code in the corner or your browser’s "
        "Share / Copy link menu, if available."
    ),
    "pet_link_fail_desk": (
        "Could not copy the link automatically. Copy it from the address bar or use the QR code."
    ),
    "pet_js_msg_empty": "Write a message before sending.",
    "pet_js_sending": "Sending…",
    "pet_js_sent": "Sent",
    "pet_js_msg_fail": "Message could not be sent.",
    "pet_js_msg_err": "Error sending message.",
    "pet_js_adopt_pending": "You already have a pending request for this animal.",
    "pet_js_adopt_accepted": "Your request for this animal was already accepted.",
    "pet_js_adopt_queued": "Request added to the waiting list.",
    "pet_js_adopt_ok": "Adoption request sent.",
    "pet_js_adopt_fail": "Could not send the request.",
    "pet_js_adopt_err": "Error sending request.",
    "pet_js_pop_ok": (
        "Your request was sent. The owner / shelter will contact you directly by email or phone."
    ),
    "pet_js_finalize_confirm": (
        "Mark adoption as finalized for {name}? The adopter will be notified."
    ),
    "pet_err_already_adopted": "This animal is already adopted.",
    "pet_err_own_listing": "You cannot request adoption of your own listing.",
    "pet_err_account_type": "This account type cannot request adoptions.",
    "pet_err_already_finalized": "Adoption for this animal is already finalized.",
    "pet_err_simple_inactive": "The simple adoption form is not active.",
    "pet_err_already_sent_today": (
        "You already sent a request for this animal today. The owner will contact you."
    ),
    "pet_err_send_generic": "Sending failed.",
    "pet_err_msg_empty": "Message is empty.",
    "pet_err_msg_self": "You cannot message yourself.",
    "pet_err_msg_forbidden": (
        "You cannot send a message in this situation (account, listing, or animal already adopted)."
    ),
    "pet_sys_adopt_body": (
        "I sent an adoption request for this animal via EU-Adopt. "
        "My contact details will be available after you accept the request in MyPet → Messages."
    ),
    "pet_copied": "Copied!",
    "sms_strip_msg": "SMS donation: steps and systems — see the Donations page.",
    "pwa_strip_msg": "EU-Adopt app on MOBILE",
    # MyPet / I Love
    "mypet_title": "MyPet | EU-ADOPT",
    "mypet_my_adoptions": "My adoptions",
    "mypet_messages": "Messages",
    "mypet_messages_new": "New messages: {n}",
    "mypet_messages_none": "No new messages",
    "mypet_messages_mine": "My messages",
    "mypet_messages_pet": "Messages - {name}",
    "mypet_add": "Add a pet",
    "mypet_search_ph": "Search name or chip/RUA",
    "mypet_search_aria": "Search animals",
    "mypet_dogs": "Dogs",
    "mypet_cats": "Cats",
    "mypet_other": "Other",
    "mypet_photo": "Photo",
    "mypet_name": "Name",
    "mypet_date_in": "Date in",
    "mypet_date_out": "Date out",
    "mypet_age": "Age",
    "mypet_in_progress": "In progress",
    "mypet_sheet": "Sheet %",
    "mypet_views": "Views",
    "mypet_adoption": "Adoption",
    "mypet_promote": "Promote",
    "mypet_cancel": "Cancel",
    "mypet_archive": "Archive",
    "mypet_reply_ph": "Reply here…",
    "mypet_accept_title": "Accept adoption request",
    "mypet_reject_title": "Reject request",
    "mypet_expired_title": "Adoption expired — extend 7 days or move to next user",
    "mypet_finalize_msg": (
        "Mark adoption as finalized? The animal stays visible as “Adopted”, "
        "and the adopter appears under “Adopted”."
    ),
    "mypet_finalize_ok": "Yes, finalize",
    "mypet_finalize_fail": "Could not finalize.",
    "account_edit_profile": "Edit profile",
    "account_firm_data": "COMPANY DETAILS",
    "account_org_data": "NGO / COMPANY DETAILS",
    # Promo A2 order note
    "promo_title": "A2 promotion order | EU-ADOPT",
    "promo_h1": "A2 promotion order note",
    "promo_aria": "A2 promotion order note",
    "promo_prelaunch_banner": "Free — pre-launch stage",
    "promo_prelaunch_max": "maximum 1 promotion per account",
    "promo_pet": "Pet",
    "promo_species": "species",
    "promo_service_lbl": "Included service",
    "promo_service_value": "{imp} appearances in the A2 Home grid, {mins} minutes each · {price}",
    "promo_help": (
        "After payment is activated, the listing joins the A2 central grid rotation (12 cells): "
        "one appearance per cell, in two consecutive waves. "
        "If the platform is busy, delivering the full package may take more than 24 hours — "
        "you still get every appearance, with an email report of date/time and cell number for each one."
    ),
    "promo_total": "Total",
    "promo_total_free": "Free activation during pre-launch.",
    "promo_total_paid": "Payment method is chosen when you complete the order in the cart.",
    "promo_add_cart": "Add to cart",
    "promo_price_free": "Free (pre-launch)",
    "promo_done": "Order completed.",
    "promo_done_qty": "Offers no.",
    "promo_done_period": "Period",
    "promo_exit_pt": "Back to Find a friend",
    "promo_exit_pt_go": "Go to Find a friend",
    "promo_exit_mypet": "Back to MyPet",
    "promo_exit_mypet_go": "Go to MyPet",
    "promo_msg_need_pub": "The listing must be published before promotion.",
    "promo_msg_already_cart": "This listing is already in the cart for A2 promotion.",
    "promo_msg_one_only": "During pre-launch you can activate only one A2 promotion per account.",
    "promo_msg_cart_full": "The cart is full (limit {n}). Remove items if you need space.",
    "promo_msg_added": "A2 promotion added to the cart.",
    "promo_msg_added_free": " Activation is free during pre-launch.",
    "promo_msg_added_pay": " Continue to Checkout to pay and confirm.",
    "promo_cart_title": "A2 promotion · {name} — {price} ({imp} appearances × {mins} min)",
    "ilove_title": "I Love – EU-ADOPT",
    "ilove_empty": "No favourites yet. Tap the heart on a photo to save it here.",
    "ilove_heading": "I Love",
    "ilove_lead": "Your hearted animals.",
    "ilove_hearted": "Hearted",
    "ilove_remove": "Remove from I Love",
    "ilove_add": "Add to I Love",
    "ilove_aria": "I Love — favourites",
    "ilove_messages": "Messages",
    "ilove_unavailable": "Listing unavailable or withdrawn",
    # Account
    "account_title": "My account – EU-ADOPT",
    "account_heading": "My account",
    "account_sheet": "Account profile",
    "account_save": "Save",
    "account_save_profile": "Save profile",
    "account_delete": "Delete account",
    "account_delete_scheduled": "Account deletion scheduled.",
    "account_save_org": "Save NGO/company details",
    "account_save_firm": "Save company details",
    # Site guide + PWA + login modal
    "guide_title": "EU-Adopt guide",
    "guide_close": "Close",
    "guide_ph": "Type your question…",
    "guide_ask": "Question",
    "guide_send": "Send",
    "pwa_aria": "EU-Adopt app on phone",
    "pwa_title": "Phone app: EU-Adopt?",
    "pwa_body": "Want a home-screen icon — opens straight to Home.",
    "pwa_ios": "iPhone: Share → Add to Home Screen",
    "pwa_yes": "Yes",
    "pwa_no": "No",
    "login_modal_title": "Continue adoption",
    "login_modal_body": "To continue, create a free account (takes about 30 seconds).",
    "login_modal_login": "Login",
    "login_modal_register": "Create account",
    "login_modal_close": "Close",
    # Auth / misc
    "signup_title": "Create account | EU-ADOPT",
    "signup_choose_title": "Choose account type – EU-ADOPT",
    "signup_choose_h1": "Choose account type",
    "signup_choose_intro": "Select the category that describes you to continue registration.",
    "signup_choose_pf_h": "Individual",
    "signup_choose_pf_p": "Personal account for adopters or people who want to use the platform.",
    "signup_choose_org_h": "Shelter / NGO / Company",
    "signup_choose_org_p": "Ltd/SA, NGO, associations, foundations, public or private shelters.",
    "signup_choose_col_h": "Clinic / Shop / Services / Transporter",
    "signup_choose_col_p": (
        "Veterinary clinics, pet grooming, shops, animal transporters and other partners."
    ),
    "signup_choose_continue": "Continue",
    "signup_choose_rules_h": "Site rules",
    "signup_choose_rules_main_h": "Main rule",
    "signup_choose_rules_1": "On this platform animals are NOT bought or sold.",
    "signup_choose_rules_2": "Listed animals are offered for adoption only.",
    "signup_choose_rules_3": (
        "Any attempt to commercialize or negotiate a price leads to permanent account deletion."
    ),
    "signup_choose_rules_read": (
        "Before registering, please read the platform rules and terms. "
        "By creating an account, you accept these rules."
    ),
    "signup_choose_terms": "Terms and conditions",
    "signup_choose_have_account": "I already have an account — sign in",
    "signup_choose_back_home": "Back to home",
    "signup_link_expired": (
        "The activation link expired (valid 24 hours). You can start a new registration below."
    ),
    "signup_link_invalid": (
        "The activation link is invalid or already used. You can start a new registration below."
    ),
    "signup_pf_title": "Individual registration – EU-ADOPT",
    "signup_pf_h1": "Individual registration",
    "signup_pf_intro": "Create a simple personal account to browse pets for adoption.",
    "signup_pf_id_h": "Identity details",
    "signup_pf_pass_h": "Password and agreements",
    "signup_lbl_last": "Last name *",
    "signup_lbl_first": "First name *",
    "signup_lbl_email": "Email *",
    "signup_lbl_phone": "Phone *",
    "signup_lbl_country": "Country *",
    "signup_lbl_county": "County *",
    "signup_lbl_city": "City / locality *",
    "signup_lbl_pass": "Password *",
    "signup_lbl_pass2": "Confirm password *",
    "signup_accept_terms": "I accept the Terms and conditions of use *",
    "signup_accept_gdpr": "I accept the Privacy policy (GDPR) *",
    "signup_accept_notify": "Email notifications from EU-Adopt (partner news)",
    "signup_submit": "Create account",
    "signup_sms_code": "SMS code (6 digits)",
    "forgot_title": "Reset password – EU-ADOPT",
    "forgot_h1": "Reset password",
    "forgot_intro": (
        "Enter your email address and we will send a password reset link (valid 1 hour)."
    ),
    "forgot_success": (
        "If an account exists with this email, you will receive a link within a few minutes. "
        "Check spam too."
    ),
    "forgot_submit": "Send reset link",
    "forgot_back": "← Back to sign in",
    "reset_title": "New password – EU-ADOPT",
    "reset_h1": "New password",
    "reset_intro": "Choose a new password (minimum 8 characters).",
    "reset_lbl_pass": "New password",
    "reset_lbl_pass2": "Confirm password",
    "reset_submit": "Save password",
    "mail_adopt_confirm_subj": "Your adoption request for {pet}",
    "mail_reset_subj": "Password reset – EU-Adopt",
    "publi": "Ad",
    "publicitate": "Advertising",
}


def eu_or_ro(request, key: str, ro: str, **fmt) -> str:
    """Localized pack when request is on EU site; otherwise Romanian `ro`."""
    if getattr(request, "eu_site_active", False):
        lang = getattr(request, "eu_site_lang", None) or getattr(request, "LANGUAGE_CODE", None)
        text = eu_ui_label(key, lang=lang, **fmt)
        if text and text != key:
            return text
    if fmt:
        try:
            return ro.format(**fmt)
        except Exception:
            return ro
    return ro


def _resolve_lang(lang: str | None) -> str:
    code = (lang or get_language() or EU_UI_DEFAULT_LANGUAGE).split("-")[0].lower()
    if code not in EU_UI_HUB_LANGUAGE_CODES and code != EU_UI_DEFAULT_LANGUAGE:
        # .de/.fr/.es may use any EU_SITE language via manual switch
        from home.eu_site import EU_SITE_LANGUAGE_CODES

        if code not in EU_SITE_LANGUAGE_CODES:
            code = EU_UI_DEFAULT_LANGUAGE
    return code


@lru_cache(maxsize=1)
def _load_i18n_packs() -> dict[str, dict[str, str]]:
    if not _I18N_JSON.is_file():
        return {}
    try:
        raw = json.loads(_I18N_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for lang, pack in raw.items():
        if isinstance(pack, dict):
            out[str(lang).lower()] = {str(k): str(v) for k, v in pack.items()}
    return out


def _pack_for_lang(lang: str | None) -> dict[str, str]:
    code = _resolve_lang(lang)
    if code == EU_UI_DEFAULT_LANGUAGE:
        return _EN
    extra = _load_i18n_packs().get(code)
    if not extra:
        return _EN
    merged = dict(_EN)
    merged.update(extra)
    return merged


def eu_ui_label(key: str, lang: str | None = None, **fmt) -> str:
    pack = _pack_for_lang(lang)
    text = pack.get(key, "")
    if not text:
        return key
    if fmt:
        try:
            return text.format(**fmt)
        except Exception:
            return text
    return text


def eu_ui_pack(lang: str | None = None) -> dict[str, str]:
    return dict(_pack_for_lang(lang))


def assert_hub_ui_languages_complete() -> None:
    """Test helper: variant B hub languages have all EN keys."""
    packs = _load_i18n_packs()
    missing: list[str] = []
    for code in sorted(EU_UI_HUB_LANGUAGE_CODES - {EU_UI_DEFAULT_LANGUAGE}):
        pack = packs.get(code)
        if not pack:
            missing.append(f"{code}: no pack")
            continue
        for key in _EN:
            if key not in pack or not str(pack[key]).strip():
                missing.append(f"{code}.{key}")
    if missing:
        raise AssertionError("Incomplete EU UI labels: " + ", ".join(missing[:40]))
