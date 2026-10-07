from django.urls import path

from . import views

app_name = 'classroom'

urlpatterns = [
    path('', views.student_dashboard, name='dashboard'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('award/', views.award_points_view, name='award'),
    path('attendance/', views.attendance_view, name='attendance'),
    path('quizzes/', views.quizzes_view, name='quizzes'),
    path('quizzes/<int:pk>/take/', views.quiz_take, name='quiz_take'),
    path('quizzes/<int:pk>/review/', views.quiz_review, name='quiz_review'),
    path('quizzes/<int:pk>/retake/', views.quiz_retake, name='quiz_retake'),
    path('assignments/', views.assignments_view, name='assignments'),
    path('assignments/<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),
    path('rewards/', views.rewards_view, name='rewards'),
    path('daily-bonus/', views.daily_bonus, name='daily_bonus'),
    path('staff/', views.staff_dashboard, name='staff'),
    path('staff/badges/', views.staff_badges, name='staff_badges'),
    path('staff/rewards/', views.staff_rewards, name='staff_rewards'),
    path('staff/classrooms/', views.staff_classrooms, name='staff_classrooms'),
    path('staff/assignments/', views.staff_assignments, name='staff_assignments'),
    path('staff/ai-quiz/', views.ai_quiz, name='ai_quiz'),
    path('ai-study/', views.ai_study, name='ai_study'),
    path('ai-architecture/', views.ai_architecture, name='ai_architecture'),
    path('staff/ai-assignment/', views.ai_assignment, name='ai_assignment'),
    path('staff/ai-insights/', views.ai_insights, name='ai_insights'),
    path('staff/ai-settings/', views.ai_settings, name='ai_settings'),
]
