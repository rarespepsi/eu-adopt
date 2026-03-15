from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('login/forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('signup/alege-tip/', views.signup_choose_type_view, name='signup_choose_type'),
    path('signup/persoana-fizica/', views.signup_pf_view, name='signup_pf'),
    path('signup/verificare-sms/', views.signup_verificare_sms_view, name='signup_verificare_sms'),
    path('signup/persoana-fizica/sms/', views.signup_pf_sms_view, name='signup_pf_sms'),
    path('signup/verificare-email/', views.signup_pf_check_email_view, name='signup_pf_check_email'),
    path('signup/check-activation-status/', views.signup_check_activation_status_view, name='signup_check_activation_status'),
    path('signup/complete-login/', views.signup_complete_login_view, name='signup_complete_login'),
    path('signup/verify-email/', views.signup_verify_email_view, name='signup_verify_email'),
    path('signup/organizatie/', views.signup_organizatie_view, name='signup_organizatie'),
    path('signup/colaborator/', views.signup_colaborator_view, name='signup_colaborator'),
    path('cont/', views.account_view, name='account'),
    path('mypet/', views.mypet_view, name='mypet'),
    path('mypet/add/', views.mypet_add_view, name='mypet_add'),
    path('mypet/edit/<int:pk>/', views.mypet_edit_view, name='mypet_edit'),
    path('i-love/', views.i_love_view, name='i_love'),
    path('wishlist/toggle/', views.wishlist_toggle_view, name='wishlist_toggle'),
    path('servicii/', views.servicii_view, name='servicii'),
    path('transport/', views.transport_view, name='transport'),

    path('custi/', views.custi_view, name='custi'),
    path('shop/', views.shop_view, name='shop'),
    path('shop/comanda-personalizate/', views.shop_comanda_personalizate_view, name='shop_comanda_personalizate'),
    path('shop/magazin-foto/', views.shop_magazin_foto_view, name='shop_magazin_foto'),

    path('pets/', views.home_view, name='pets_all'),
    path('pets/<int:pk>/', views.dog_profile_view, name='pets_single'),
]