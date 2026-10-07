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


# ---------------------------------------------------------------------------
# AI automation: lightweight, dependency-free question generator.
# Swap this implementation for an LLM API call later; views stay unchanged.
# ---------------------------------------------------------------------------

_TOPIC_BANKS = {
    'math': [
        ('What is 12 + 8?', '20'),
        ('What is 15 - 7?', '8'),
        ('What is 6 x 7?', '42'),
        ('What is 81 / 9?', '9'),
        ('What is the square root of 144?', '12'),
    ],
    'science': [
        ('Which planet is known as the Red Planet?', 'Mars'),
        ('What gas do plants absorb from the air?', 'carbon dioxide'),
        ('What is the chemical symbol for water?', 'H2O'),
        ('What force keeps us on the ground?', 'gravity'),
        ('What is the center of an atom called?', 'nucleus'),
    ],
    'english': [
        ('What is the plural of "child"?', 'children'),
        ('Give a synonym of "quick".', 'fast'),
        ('Which punctuation ends a question?', '?'),
        ('What is the opposite of "ancient"?', 'modern'),
        ('Name a verb in the sentence "She runs fast".', 'runs'),
    ],
    'history': [
        ('In which year did World War II end?', '1945'),
        ('Who was the first President of the Philippines?', 'Emilio Aguinaldo'),
        ('Which empire built the Colosseum?', 'Roman'),
        ('What year did the Philippines gain independence?', '1898'),
        ('Which ocean is the largest?', 'Pacific'),
    ],
}


def generate_quiz_questions(topic='math', count=5):
    """Return a list of (text, answer) tuples for a quiz on the given topic."""
    bank = _TOPIC_BANKS.get(topic.lower(), _TOPIC_BANKS['math'])
    return bank[:max(1, count)]


def _get_gemini_key():
    import os
    from pathlib import Path
    key = os.environ.get('GEMINI_API_KEY')
    if key:
        return key.strip()
    env_file = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith('GEMINI_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return None


def generate_quiz_questions_gemini(topic='math', count=5):
    """Call the Gemini API to generate quiz questions.

    Returns list of (text, answer) tuples, or falls back to the local bank
    when no API key is configured or the request fails.
    """
    import json

    api_key = _get_gemini_key()
    if not api_key:
        return generate_quiz_questions(topic, count)

    prompt = (
        f'Generate {count} short {topic} quiz questions for students. '
        'Return ONLY a JSON array like '
        '[{"question": "...", "answer": "..."}] with no markdown.'
    )
    payload = {'contents': [{'parts': [{'text': prompt}]}]}

    try:
        import requests
        for model in ('gemini-3.8-flash', 'gemini-flash-latest', 'gemini-3.5-flash'):
            url = (
                'https://generativelanguage.googleapis.com/v1beta/models/'
                f'{model}:generateContent?key={api_key}'
            )
            try:
                resp = requests.post(url, json=payload, timeout=30)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                text = data['candidates'][0]['content']['parts'][0]['text']
                text = text.strip()
                if text.startswith('```'):
                    text = text.strip('`').lstrip('json').strip()
                items = json.loads(text)
                return [(item['question'], item['answer']) for item in items[:count]]
            except Exception:
                continue
        return generate_quiz_questions(topic, count)
    except Exception:
        return generate_quiz_questions(topic, count)
