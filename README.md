# Django Project V3 — Gamified Classroom Assistant

A Django-based web system that gamifies the classroom: XP, levels, badges,
streaks, leaderboard, quizzes, assignments, attendance, and a rewards shop.

## Members
- Arc Xerlan D. Lucasan
- Adrian P. Lirazan
- Carl Mosquera

## Setup
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_classroom
python manage.py runserver
```

## AI Automation
See `docs/AI_AUTOMATION.md`. Includes a rule-based AI quiz generator
(`services.generate_quiz_questions`, staff page at `/classroom/staff/ai-quiz/`)
and CI in `.github/workflows/ci.yml`.

## Admin & Staff
- Django admin: `/admin/` (superuser `admin`)
- Staff management pages: `/classroom/staff/` (CRUD for badges, rewards,
  classrooms, assignments, AI quiz generation)
- Profile update for any admin/staff: `/users/profile/`

