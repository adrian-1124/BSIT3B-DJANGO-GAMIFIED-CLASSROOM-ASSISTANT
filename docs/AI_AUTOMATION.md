# AI Automation Architecture — Gamified Classroom Assistant

## Overview
The system integrates automation at three layers: **content generation**,
**engagement intelligence**, and **operations**.

```
┌─────────────┐   questions   ┌──────────────┐
│ Staff UI    │──────────────>│ AI Quiz Gen  │
└─────┬───────┘               └──────┬───────┘
      │                              │ Quiz/Question rows
      v                              v
┌─────────────┐  points/XP    ┌──────────────┐
│ Student Hub │<──────────────│ Points Engine│
└─────┬───────┘               └──────┬───────┘
      │ answers/submissions          │ badges/levels
      v                              v
┌─────────────┐  analytics   ┌──────────────┐
│ Dashboard   │─────────────>│ Leaderboard  │
└─────────────┘              └──────────────┘
```

## Layers
1. **Content automation** — `services.generate_quiz_questions(topic, count)`
   produces ready-to-use `Question` rows (rule-based now; swap the function
   body for an LLM API call later without touching views).
2. **Engagement automation** — points, levels, badges, streaks handled by
   `services.award_points()` / `touch_streak()`; triggered automatically by
   quiz results, submissions, and attendance.
3. **Operations automation** — GitHub Actions CI runs migrations + the full
   test suite on every push; `seed_classroom` command bootstraps demo data.

## Extension points
- Replace `generate_quiz_questions` with an LLM (OpenAI/etc.) call.
- Add a nightly job (cron or Celery) that resets streaks and computes
  weekly leaderboards.
- Add feedback copy in `quiz_result.html` generated from score bands.
