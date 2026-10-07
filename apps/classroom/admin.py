from django.contrib import admin

from .models import (
    Assignment, AttendanceEntry, Badge, ClassRoom, PointTransaction,
    Question, Quiz, QuizAttempt, Redemption, Reward, StudentBadge,
    StudentProfile, Submission,
)


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'section', 'teacher')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'classroom', 'xp', 'points', 'streak_days')
    search_fields = ('user__username',)


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'delta', 'reason', 'created_at')


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_required', 'icon')


@admin.register(StudentBadge)
class StudentBadgeAdmin(admin.ModelAdmin):
    list_display = ('profile', 'badge', 'awarded_at')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'classroom', 'reward_points')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz')


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('profile', 'quiz', 'score', 'total', 'points_earned')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'classroom', 'due_date', 'points')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'status', 'grade')


@admin.register(AttendanceEntry)
class AttendanceEntryAdmin(admin.ModelAdmin):
    list_display = ('student', 'classroom', 'date', 'status')


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ('name', 'cost')


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'reward', 'redeemed_at', 'fulfilled')
