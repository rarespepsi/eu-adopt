"""
Servicii pentru sistemul de concurs referral.
"""
import hashlib
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q
from .models import Contest, ReferralVisit


def get_active_contest():
    """Returnează concursul activ, dacă există."""
    now = timezone.now()
    return Contest.objects.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).first()


def get_contest_leaderboard(limit=10, contest=None):
    """
    Returnează leaderboard-ul pentru concurs.
    Cache: 5 minute.
    """
    if contest is None:
        contest = get_active_contest()
    
    if not contest:
        return []
    
    cache_key = f"contest_leaderboard_{contest.id}_{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Calculează punctele pentru fiecare utilizator (vizite unice contorizate)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Filtrează vizitele în perioada concursului și contorizate
    top_users = User.objects.filter(
        referral_visits__counted=True,
        referral_visits__timestamp__gte=contest.start_date,
        referral_visits__timestamp__lte=contest.end_date
    ).annotate(
        total_points=Count(
            'referral_visits',
            filter=Q(
                referral_visits__counted=True,
                referral_visits__timestamp__gte=contest.start_date,
                referral_visits__timestamp__lte=contest.end_date
            )
        )
    ).filter(
        total_points__gt=0
    ).order_by('-total_points')[:limit]
    
    result = [
        {
            'user': user,
            'points': user.total_points,
            'position': idx + 1
        }
        for idx, user in enumerate(top_users)
    ]
    
    cache.set(cache_key, result, 300)  # 5 minute
    return result


def get_remaining_days(contest=None):
    """Calculează zilele rămase până la sfârșitul concursului."""
    if contest is None:
        contest = get_active_contest()
    
    if not contest:
        return 0
    
    now = timezone.now()
    if now >= contest.end_date:
        return 0
    
    delta = contest.end_date - now
    return max(0, delta.days)


def hash_ip(ip_address):
    """Generează hash pentru IP (pentru privacy)."""
    return hashlib.sha256(ip_address.encode()).hexdigest()


def track_referral_visit(request, ref_code, user):
    """
    Trackează o vizită referral.
    Reguli:
    - 1 punct = 1 vizită unică
    - Doar o vizită per IP hash per 24h contează
    """
    if not ref_code or not user:
        return None
    
    contest = get_active_contest()
    if not contest:
        return None
    
    now = timezone.now()
    
    # Verifică dacă concursul e activ
    if now < contest.start_date or now > contest.end_date:
        return None
    
    # Obține IP și generează hash
    ip_address = get_client_ip(request)
    ip_hash = hash_ip(ip_address)
    
    # Verifică dacă există deja o vizită contorizată pentru acest IP în ultimele 24h
    yesterday = now - timedelta(days=1)
    existing_visit = ReferralVisit.objects.filter(
        ref_code=ref_code,
        ip_hash=ip_hash,
        counted=True,
        timestamp__gte=yesterday
    ).first()
    
    if existing_visit:
        # Vizită deja contorizată în ultimele 24h
        return None
    
    # Creează noua vizită
    visit = ReferralVisit.objects.create(
        ref_code=ref_code,
        user=user,
        ip_hash=ip_hash,
        counted=True
    )
    
    # Invalidează cache-ul leaderboard-ului
    try:
        cache.delete_many([f"contest_leaderboard_{contest.id}_{i}" for i in [10, 20, 50]])
    except Exception:
        pass
    
    return visit


def get_client_ip(request):
    """Obține IP-ul clientului din request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '0.0.0.0'


def get_user_referral_code(user):
    """
    Generează un cod referral pentru utilizator.
    Poate fi username-ul sau un hash al ID-ului.
    """
    if not user or not user.is_authenticated:
        return None
    
    # Folosim username-ul ca cod referral (simplu și ușor de partajat)
    return user.username
