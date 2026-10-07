"""Gamified classroom models: XP, levels, badges, streaks, leaderboard,
quizzes, assignments, attendance, and a rewards shop."""

from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class ClassRoom(models.Model):
    name = models.CharField(max_length=100)
    section = models.CharField(max_length=50, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classrooms')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} {self.section}'.strip()


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, related_name='students', null=True, blank=True)
    avatar_emoji = models.CharField(max_length=8, default='🎓')
    xp = models.PositiveIntegerField(default=0)
    points = models.IntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    last_bonus_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-xp']

    def __str__(self):
        return f'{self.user.username} (Lv {self.level})'

    @property
    def level(self):
        from .services import level_for_xp
        return level_for_xp(self.xp)

    @property
    def xp_into_level(self):
        from .services import xp_into_level
        return xp_into_level(self.xp)

    @property
    def xp_to_next_level(self):
        from .services import xp_needed_for_next
        return xp_needed_for_next(self.xp)

    @property
    def level_progress_pct(self):
        from .services import XP_PER_LEVEL, xp_into_level
        return int(min(xp_into_level(self.xp) / XP_PER_LEVEL * 100, 100))


class PointTransaction(models.Model):
    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='transactions')
    delta = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.delta:+d} {self.profile.user.username} — {self.reason}'


class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=50, default='fa-medal')
    points_required = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class StudentBadge(models.Model):
    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'badge')

    def __str__(self):
        return f'{self.profile.user.username} — {self.badge.name}'


class Quiz(models.Model):
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    reward_points = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    answer = models.CharField(max_length=255)

    def __str__(self):
        return self.text[:60]


class QuizAttempt(models.Model):
    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    points_earned = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'quiz')

    def __str__(self):
        return f'{self.profile.user.username} — {self.quiz.title}: {self.score}/{self.total}'


class Assignment(models.Model):
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    points = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.title


class Submission(models.Model):
    STATUS_CHOICES = [('submitted', 'Submitted'), ('graded', 'Graded')]
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submissions/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    grade = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f'{self.student.username} — {self.assignment.title}'


class AttendanceEntry(models.Model):
    STATUS_CHOICES = [('present', 'Present'), ('absent', 'Absent'), ('late', 'Late'), ('excused', 'Excused')]
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='attendance')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')

    class Meta:
        unique_together = ('classroom', 'student', 'date')

    def __str__(self):
        return f'{self.student.username} {self.date} — {self.status}'


class Reward(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    cost = models.PositiveIntegerField(default=50)

    def __str__(self):
        return f'{self.name} ({self.cost} pts)'


class Redemption(models.Model):
    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='redemptions')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    fulfilled = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.profile.user.username} redeemed {self.reward.name}'


class AIProvider(models.Model):
    """API-key configuration for AI providers (DB overrides .env)."""
    PROVIDER_CHOICES = [('openrouter', 'OpenRouter'), ('gemini', 'Gemini')]
    name = models.CharField(max_length=20, choices=PROVIDER_CHOICES, unique=True)
    api_key = models.CharField(max_length=255, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} ({"on" if self.enabled else "off"})'

    @property
    def masked_key(self):
        from .ai import masked_key
        return masked_key(self.api_key)


class AILog(models.Model):
    """Usage log for AI automation calls."""
    feature = models.CharField(max_length=50)
    provider = models.CharField(max_length=20)
    success = models.BooleanField(default=True)
    latency_ms = models.PositiveIntegerField(default=0)
    error_preview = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = 'ok' if self.success else 'fail'
        return f'{self.feature} via {self.provider} — {status}'
