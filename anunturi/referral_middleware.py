"""
Middleware pentru tracking referral visits.
Verifică parametrul ?ref= din URL și setează cookie pentru 30 zile.
"""
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from .contest_service import track_referral_visit, get_active_contest

User = get_user_model()


class ReferralTrackingMiddleware(MiddlewareMixin):
    """
    Middleware care trackează vizite referral.
    Verifică parametrul ?ref= din URL și setează cookie pentru 30 zile.
    """
    
    def process_request(self, request):
        """Procesează request-ul și verifică parametrul ref."""
        ref_code = request.GET.get('ref')
        
        if not ref_code:
            return None
        
        # Verifică dacă există un concurs activ
        contest = get_active_contest()
        if not contest:
            return None
        
        # Verifică dacă utilizatorul cu acest cod există
        try:
            user = User.objects.get(username=ref_code)
        except User.DoesNotExist:
            return None
        
        # Setează cookie pentru 30 zile (dacă nu există deja)
        cookie_name = f'ref_{ref_code}'
        if cookie_name not in request.COOKIES:
            # Cookie-ul va fi setat în response
            request._set_referral_cookie = cookie_name
            request._referral_user = user
            request._referral_code = ref_code
        
        return None
    
    def process_response(self, request, response):
        """Setează cookie-ul în response dacă e necesar."""
        if hasattr(request, '_set_referral_cookie'):
            # Setează cookie pentru 30 zile
            response.set_cookie(
                request._set_referral_cookie,
                '1',
                max_age=30 * 24 * 60 * 60,  # 30 zile
                httponly=False,  # Poate fi accesat de JavaScript dacă e nevoie
                samesite='Lax'
            )
            
            # Trackează vizita (doar dacă cookie-ul nu exista deja)
            if hasattr(request, '_referral_user') and hasattr(request, '_referral_code'):
                try:
                    track_referral_visit(request, request._referral_code, request._referral_user)
                except Exception:
                    # Ignoră erorile pentru a nu afecta request-ul
                    pass
        
        return response
