"""Gamification rules: XP/level math, point awards, badges, streaks."""

from datetime import date, timedelta

XP_PER_LEVEL = 100


def level_for_xp(xp):
    return xp // XP_PER_LEVEL + 1


def xp_into_level(xp):
    return xp % XP_PER_LEVEL


def xp_needed_for_next(xp):
    return XP_PER_LEVEL - xp_into_level(xp)


def award_points(profile, delta, reason):
    """Award/deduct points and XP, log it, and auto-grant badges.

    Returns dict with level_up flag and newly granted badges.
    """
    from .models import Badge, PointTransaction, StudentBadge

    old_level = level_for_xp(profile.xp)
    profile.xp = max(0, profile.xp + delta)
    profile.points = max(0, profile.points + delta)
    profile.save(update_fields=['xp', 'points'])

    PointTransaction.objects.create(profile=profile, delta=delta, reason=reason)

    level_up = level_for_xp(profile.xp) > old_level

    new_badges = []
    for badge in Badge.objects.filter(points_required__gt=0, points_required__lte=profile.points):
        _, created = StudentBadge.objects.get_or_create(profile=profile, badge=badge)
        if created:
            new_badges.append(badge)

    return {'level_up': level_up, 'new_badges': new_badges}


def touch_streak(profile):
    """Update daily streak; returns True if it was a new day."""
    today = date.today()
    last = profile.last_active_date

    if last == today:
        return False

    if last is not None and last == today - timedelta(days=1):
        profile.streak_days += 1
    else:
        profile.streak_days = 1

    profile.last_active_date = today
    profile.save(update_fields=['streak_days', 'last_active_date'])
    return True
