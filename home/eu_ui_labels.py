"""
UI page strings for EU sites — English forced on .com (full UI).
Romanian stays hard-coded on .ro templates via eu_t fallback.
"""
from __future__ import annotations

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
    # Contact
    "contact_title": "Contact | EU-ADOPT",
    "contact_heading": "Contact EU-ADOPT",
    "contact_intro": "Choose the right channel and email us. We usually reply within 1–3 working days.",
    "contact_emails_h": "EU-Adopt email addresses",
    "contact_emails_lead": "Tap Send email — your mail app opens with the recipient filled in.",
    "contact_send_email": "Send email",
    "contact_emails_note": "All messages are handled by the EU-Adopt team. For animal medical emergencies, contact a vet immediately.",
    "contact_aria": "Contact page",
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
    # Transport
    "transport_title": "Transport | EU-ADOPT",
    "transport_request": "Transport request",
    "transport_submit": "Submit request",
    "transport_aria": "Transport content",
    "transport_t1_title": "Vet transport – request",
    "transport_t1_intro": "Your request goes to partners; the first to accept gets the details.",
    "transport_want": "I want transport",
    "transport_donate": "Donate to a cause",
    "transport_collapse": "Collapse form",
    "transport_actions_aria": "Transport actions",
    "transport_today": "Transport today",
    "transport_intl": "International transport",
    "transport_intl_tip": "Safe pet transport in-country and across borders, with a dedicated vehicle.",
    "transport_county": "COUNTY",
    "transport_city": "CITY / PLACE",
    "transport_from": "PICK-UP POINT",
    "transport_to": "DROP-OFF POINT",
    # MyPet / I Love
    "mypet_title": "MyPet | EU-ADOPT",
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
    # Auth / account
    "account_title": "Account | EU-ADOPT",
    "signup_title": "Create account | EU-ADOPT",
    "publi": "Ad",
    "publicitate": "Advertising",
}


def eu_ui_label(key: str, **fmt) -> str:
    text = _EN.get(key, "")
    if not text:
        return key
    if fmt:
        try:
            return text.format(**fmt)
        except Exception:
            return text
    return text


def eu_ui_pack() -> dict[str, str]:
    return dict(_EN)
