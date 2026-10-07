from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.classroom.models import (
    Assignment, Badge, ClassRoom, Question, Quiz, Reward, StudentProfile,
)

User = get_user_model()

BADGES = [
    ('First Steps', 'Earned your first points', 'fa-medal', 5),
    ('Rising Star', 'Earned 50 points', 'fa-star', 50),
    ('High Achiever', 'Earned 200 points', 'fa-trophy', 200),
    ('Legend', 'Earned 1000 points', 'fa-crown', 1000),
]

REWARDS = [
    ('Homework Pass', 'Skip one homework grade', 75),
    ('Seat of Choice', 'Sit anywhere for a week', 50),
    ('Extra Credit', '+5 points on next quiz', 100),
]


class Command(BaseCommand):
    help = 'Seed demo gamified-classroom data'

    def handle(self, *args, **options):
        teacher, _ = User.objects.get_or_create(username='teacher', defaults={'is_staff': True})
        teacher.is_staff = True
        if not teacher.has_usable_password():
            teacher.set_password('teacher123')
        teacher.save()

        classroom, _ = ClassRoom.objects.get_or_create(name='BSIT', section='3A', teacher=teacher)

        for username in ['ana', 'ben', 'cara', 'dan']:
            user, _ = User.objects.get_or_create(username=username)
            if not user.has_usable_password():
                user.set_password('student123')
                user.save()
            profile, _ = StudentProfile.objects.get_or_create(user=user, defaults={'classroom': classroom})
            if profile.classroom is None:
                profile.classroom = classroom
                profile.save()

        for name, desc, icon, req in BADGES:
            Badge.objects.get_or_create(name=name, defaults={'description': desc, 'icon': icon, 'points_required': req})

        for name, desc, cost in REWARDS:
            Reward.objects.get_or_create(name=name, defaults={'description': desc, 'cost': cost})

        quiz, _ = Quiz.objects.get_or_create(title='Intro Quiz', classroom=classroom, defaults={'reward_points': 20})
        Question.objects.get_or_create(quiz=quiz, text='What is 2 + 2?', defaults={'answer': '4'})
        Question.objects.get_or_create(quiz=quiz, text='Capital of the Philippines?', defaults={'answer': 'Manila'})

        Assignment.objects.get_or_create(title='Essay 1', classroom=classroom, defaults={'description': 'Write 1 page', 'points': 20})

        self.stdout.write(self.style.SUCCESS('Seeded gamified classroom demo data.'))
        self.stdout.write('teacher/teacher123 (staff) & ana/ben/cara/dan with password student123')
