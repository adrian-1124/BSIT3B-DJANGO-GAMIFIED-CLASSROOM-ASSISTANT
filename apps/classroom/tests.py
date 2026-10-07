from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Badge, StudentBadge, StudentProfile
from .services import award_points, level_for_xp, touch_streak

User = get_user_model()


class LevelMathTests(TestCase):
    def test_levels(self):
        self.assertEqual(level_for_xp(0), 1)
        self.assertEqual(level_for_xp(99), 1)
        self.assertEqual(level_for_xp(100), 2)
        self.assertEqual(level_for_xp(250), 3)


class AwardPointsTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='stu', password='x')
        self.profile = StudentProfile.objects.create(user=user)

    def test_award_updates_points_and_xp(self):
        award_points(self.profile, 30, 'test')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 30)
        self.assertEqual(self.profile.xp, 30)

    def test_badge_auto_granted(self):
        Badge.objects.create(name='Bronze', points_required=10)
        result = award_points(self.profile, 15, 'test')
        self.assertEqual(len(result['new_badges']), 1)
        self.assertTrue(StudentBadge.objects.filter(profile=self.profile).exists())

    def test_points_never_negative(self):
        award_points(self.profile, -50, 'deduct')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 0)


class StreakTests(TestCase):
    def test_streak_increments(self):
        user = User.objects.create_user(username='s2', password='x')
        profile = StudentProfile.objects.create(user=user)
        touch_streak(profile)
        profile.refresh_from_db()
        self.assertEqual(profile.streak_days, 1)


class AILayerTests(TestCase):
    def test_masked_key(self):
        from .ai import masked_key
        self.assertEqual(masked_key(''), 'not set')
        self.assertEqual(masked_key('sk-or-v1-abcdef123456'), 'sk-o...3456')

    def test_extract_json_array(self):
        from .ai import _extract_json_array
        items = _extract_json_array('```json\n[{"question": "Q?", "answer": "A"}]\n```')
        self.assertEqual(items, [{'question': 'Q?', 'answer': 'A'}])

    def test_quiz_falls_back_to_local_bank_without_network(self):
        from unittest import mock
        from . import ai as ai_module
        with mock.patch.object(ai_module, 'ai_chat_json', side_effect=RuntimeError('offline')):
            items, provider = ai_module.ai_generate_quiz_questions('math', 2)
            self.assertEqual(provider, 'local-bank')
            self.assertEqual(len(items), 2)

    def test_feedback_falls_back_offline(self):
        from unittest import mock
        from . import ai as ai_module
        with mock.patch.object(ai_module, 'ai_chat', side_effect=RuntimeError('offline')):
            text, provider = ai_module.ai_quiz_feedback('Demo', 1, 2)
            self.assertEqual(provider, 'local-bank')
            self.assertIn('1/2', text)

    def test_legacy_services_delegate(self):
        from unittest import mock
        from . import ai as ai_module
        from .services import generate_quiz_questions_ai
        with mock.patch.object(
            ai_module, 'ai_generate_quiz_questions',
            return_value=([('Q1', 'A1'), ('Q2', 'A2')], 'local-bank'),
        ):
            items = generate_quiz_questions_ai('math', 2)
            self.assertEqual(items, [('Q1', 'A1'), ('Q2', 'A2')])
