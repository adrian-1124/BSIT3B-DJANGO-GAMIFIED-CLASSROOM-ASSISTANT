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
    path('assignments/', views.assignments_view, name='assignments'),
    path('assignments/<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),
    path('rewards/', views.rewards_view, name='rewards'),
    path('staff/', views.staff_dashboard, name='staff'),
    path('staff/badges/', views.staff_badges, name='staff_badges'),
    path('staff/rewards/', views.staff_rewards, name='staff_rewards'),
    path('staff/classrooms/', views.staff_classrooms, name='staff_classrooms'),
    path('staff/assignments/', views.staff_assignments, name='staff_assignments'),
    path('staff/ai-quiz/', views.ai_quiz, name='ai_quiz'),
]
