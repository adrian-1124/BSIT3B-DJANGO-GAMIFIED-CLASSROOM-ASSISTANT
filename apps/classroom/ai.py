"""Central AI automation layer.

Provider chain (in order): OpenRouter (free model) -> Gemini -> local fallback.
API keys resolve from: DB (AIProvider) -> environment -> .env file.
Every call is logged to AILog (best-effort; logging never breaks generation).
"""

import json
import time

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
GEMINI_MODELS = ('gemini-3.8-flash', 'gemini-flash-latest', 'gemini-3.5-flash')
DEFAULT_OPENROUTER_MODEL = 'openrouter/free'


def _get_env_value(name, default=None):
    import os
    from pathlib import Path
    value = os.environ.get(name)
    if value:
        return value.strip()
    env_file = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith(f'{name}='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return default


def _get_db_provider(name):
    """Return (api_key, model_name, enabled) from DB, or None if unavailable."""
    try:
        from .models import AIProvider
        obj = AIProvider.objects.filter(name=name).first()
        if obj:
            return (obj.api_key or '').strip(), (obj.model_name or '').strip(), obj.enabled
    except Exception:
        pass
    return None


def get_api_key(provider):
    """Resolve API key: DB first, then env/.env. Returns '' when unset."""
    db = _get_db_provider(provider)
    if db and db[0]:
        return db[0]
    if provider == 'openrouter':
        return _get_env_value('OPENROUTER_API_KEY', '') or ''
    if provider == 'gemini':
        return _get_env_value('GEMINI_API_KEY', '') or ''
    return ''


def get_model_name(provider):
    db = _get_db_provider(provider)
    if db and db[1]:
        return db[1]
    if provider == 'openrouter':
        return _get_env_value('OPENROUTER_MODEL', DEFAULT_OPENROUTER_MODEL) or DEFAULT_OPENROUTER_MODEL
    return ''


def is_provider_enabled(provider):
    db = _get_db_provider(provider)
    if provider == 'openrouter':
        env_key = _get_env_value('OPENROUTER_API_KEY', '')
    elif provider == 'gemini':
        env_key = _get_env_value('GEMINI_API_KEY', '')
    else:
        env_key = ''
    if db is not None:
        return bool(db[2]) and bool((db[0] or '').strip() or (env_key or '').strip())
    return bool((env_key or '').strip())


def masked_key(key):
    if not key:
        return 'not set'
    key = key.strip()
    if len(key) <= 8:
        return '****'
    return f'{key[:4]}...{key[-4:]}'


def provider_status():
    """Summarise provider readiness without exposing full keys."""
    return [
        {'name': 'openrouter', 'enabled': is_provider_enabled('openrouter'),
         'model': get_model_name('openrouter'), 'key': masked_key(get_api_key('openrouter'))},
        {'name': 'gemini', 'enabled': is_provider_enabled('gemini'),
         'model': 'auto (fallback chain)', 'key': masked_key(get_api_key('gemini'))},
        {'name': 'local-bank', 'enabled': True, 'model': 'built-in', 'key': 'n/a'},
    ]


def _log(feature, provider, success, latency_ms=0, error=''):
    try:
        from .models import AILog
        AILog.objects.create(
            feature=feature, provider=provider, success=success,
            latency_ms=int(latency_ms), error_preview=(error or '')[:255],
        )
    except Exception:
        pass


def _extract_json_array(text):
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.strip('`').lstrip('json').strip()
    start, end = text.find('['), text.rfind(']')
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def _call_openrouter(prompt, timeout=60):
    import requests
    key = get_api_key('openrouter')
    if not key:
        raise RuntimeError('OpenRouter key not configured')
    resp = requests.post(
        OPENROUTER_URL,
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
        json={'model': get_model_name('openrouter'),
              'messages': [{'role': 'user', 'content': prompt}]},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f'OpenRouter HTTP {resp.status_code}: {resp.text[:200]}')
    return resp.json()['choices'][0]['message']['content']


def _call_gemini(prompt, timeout=30):
    import requests
    key = get_api_key('gemini')
    if not key:
        raise RuntimeError('Gemini key not configured')
    payload = {'contents': [{'parts': [{'text': prompt}]}]}
    last_error = 'no model responded'
    for model in GEMINI_MODELS:
        url = (f'https://generativelanguage.googleapis.com/v1beta/models/'
               f'{model}:generateContent?key={key}')
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code != 200:
                last_error = f'{model} HTTP {resp.status_code}'
                continue
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        except Exception as exc:
            last_error = f'{model}: {exc}'
    raise RuntimeError(last_error)


def ai_chat(prompt, feature='chat', timeout=60):
    """Try OpenRouter, then Gemini. Returns (text, provider_used)."""
    errors = []
    if is_provider_enabled('openrouter'):
        started = time.time()
        try:
            text = _call_openrouter(prompt, timeout=timeout)
            _log(feature, 'openrouter', True, (time.time() - started) * 1000)
            return text, 'openrouter'
        except Exception as exc:
            _log(feature, 'openrouter', False, (time.time() - started) * 1000, str(exc))
            errors.append(f'openrouter: {exc}')
    if is_provider_enabled('gemini'):
        started = time.time()
        try:
            text = _call_gemini(prompt, timeout=min(timeout, 30))
            _log(feature, 'gemini', True, (time.time() - started) * 1000)
            return text, 'gemini'
        except Exception as exc:
            _log(feature, 'gemini', False, (time.time() - started) * 1000, str(exc))
            errors.append(f'gemini: {exc}')
    raise RuntimeError('No AI provider available. ' + '; '.join(errors))


def ai_chat_json(prompt, feature='chat', timeout=60):
    text, provider = ai_chat(prompt, feature=feature, timeout=timeout)
    return _extract_json_array(text), provider


def _local_bank(topic, count):
    from .services import generate_quiz_questions
    return generate_quiz_questions(topic, count)


def ai_generate_quiz_questions(topic='math', count=5):
    """Generate quiz questions. Returns (items, provider_used)."""
    prompt = (
        f'Generate {count} short {topic} quiz questions for students. '
        'Return ONLY a JSON array like '
        '[{"question": "...", "answer": "..."}] with no markdown.'
    )
    try:
        items, provider = ai_chat_json(prompt, feature='quiz', timeout=60)
        cleaned = [(str(i['question']), str(i['answer'])) for i in items[:count]]
        if cleaned:
            return cleaned, provider
    except Exception:
        pass
    return _local_bank(topic, count), 'local-bank'


def ai_quiz_feedback(quiz_title, score, total):
    """Encouraging feedback for a quiz result. Returns (text, provider)."""
    if total <= 0:
        return 'Thanks for completing the quiz!', 'local-bank'
    pct = round(score / total * 100)
    fallback = (
        f'You scored {score}/{total} ({pct}%) on "{quiz_title}". '
        + ('Outstanding work — keep the streak going!' if pct >= 80
           else 'Good effort — review the missed items and try again!' if pct >= 50
           else 'Don\'t give up — every attempt earns XP. Review and retry!')
    )
    prompt = (
        f'A student scored {score} out of {total} on the quiz "{quiz_title}". '
        'Write 2 short encouraging sentences of feedback. Plain text only.'
    )
    try:
        text, provider = ai_chat(prompt, feature='feedback', timeout=30)
        return text.strip(), provider
    except Exception:
        return fallback, 'local-bank'


def ai_study_guide(topic):
    """Study guide for a topic. Returns (text, provider)."""
    fallback = (
        f'Study guide for {topic}:\n'
        '1. Break the topic into 3 small parts.\n'
        '2. Spend 15 minutes on each part with examples.\n'
        '3. Quiz yourself, then review mistakes for +XP!'
    )
    prompt = (
        f'Write a short study guide (max 150 words, numbered steps) '
        f'for a student learning "{topic}". Plain text only.'
    )
    try:
        text, provider = ai_chat(prompt, feature='study-guide', timeout=45)
        return text.strip(), provider
    except Exception:
        return fallback, 'local-bank'


def ai_assignment_idea(topic, classroom_name=''):
    """Suggest an assignment. Returns (dict, provider)."""
    fallback = ({'title': f'{topic.title()} Practice Task',
                 'description': f'Complete 5 practice problems about {topic} and show your work.',
                 'points': 20}, 'local-bank')
    prompt = (
        f'Suggest one classroom assignment about "{topic}"'
        f'{f" for class {classroom_name}" if classroom_name else ""}. '
        'Return ONLY JSON like {"title": "...", "description": "...", "points": 20}.'
    )
    try:
        data, provider = ai_chat_json(prompt, feature='assignment', timeout=45)
        if isinstance(data, dict):
            return {'title': str(data.get('title', ''))[:150] or fallback[0]['title'],
                    'description': str(data.get('description', '')),
                    'points': int(data.get('points', 20) or 20)}, provider
    except Exception:
        pass
    return fallback


def ai_class_insights(stats_text):
    """Turn class stats into teacher insights. Returns (text, provider)."""
    fallback = ('Review the leaderboard and attendance trends, praise top '
                'streaks, and re-engage students with 0 XP this week.')
    prompt = (
        'You are a teaching assistant. Given these class stats, write 3 short '
        f'bulleted insights for the teacher. Plain text only.\n\n{stats_text}'
    )
    try:
        text, provider = ai_chat(prompt, feature='insights', timeout=45)
        return text.strip(), provider
    except Exception:
        return fallback, 'local-bank'
