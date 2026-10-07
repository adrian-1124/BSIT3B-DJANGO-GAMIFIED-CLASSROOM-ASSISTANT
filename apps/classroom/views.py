from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .models import (
    Assignment, AttendanceEntry, ClassRoom, Quiz,
    QuizAttempt, Reward, StudentProfile, Submission,
)
from .services import award_points, touch_streak

User = get_user_model()


def _profile_for(user):
    profile, _ = StudentProfile.objects.get_or_create(user=user)
    return profile


def _is_staff(user):
    return user.is_staff


teacher_required = user_passes_test(_is_staff, login_url='login')


@login_required(login_url='login')
def student_dashboard(request):
    profile = _profile_for(request.user)
    is_new_day = touch_streak(profile)
    if is_new_day:
        award_points(profile, 2, 'Daily login streak bonus')

    top = StudentProfile.objects.select_related('user').order_by('-xp')[:5]
    transactions = profile.transactions.all()[:10]
    badges = profile.badges.select_related('badge').all()
    my_rank = StudentProfile.objects.filter(xp__gt=profile.xp).count() + 1

    return render(request, 'classroom/dashboard.html', {
        'profile': profile,
        'top': top,
        'transactions': transactions,
        'badges': badges,
        'my_rank': my_rank,
        'quizzes': Quiz.objects.all()[:5],
    })


@login_required(login_url='login')
def leaderboard(request):
    profiles = StudentProfile.objects.select_related('user', 'classroom').order_by('-xp')[:50]
    return render(request, 'classroom/leaderboard.html', {'profiles': profiles})


@teacher_required
def award_points_view(request):
    students = StudentProfile.objects.select_related('user').order_by('user__username')

    if request.method == 'POST':
        student_id = request.POST.get('student')
        try:
            delta = int(request.POST.get('delta', 0))
        except ValueError:
            delta = 0
        reason = request.POST.get('reason', '').strip() or 'Teacher award'

        profile = get_object_or_404(StudentProfile, pk=student_id)
        result = award_points(profile, delta, reason)
        for badge in result['new_badges']:
            messages.success(request, f'Badge earned: {badge.name}!')
        if result['level_up']:
            messages.success(request, f'{profile.user.username} leveled up!')
        messages.success(request, f'Awarded {delta:+d} to {profile.user.username}.')
        return redirect('classroom:award')

    return render(request, 'classroom/award.html', {'students': students})


@teacher_required
def attendance_view(request):
    teachers = ClassRoom.objects.all()
    classroom_id = request.GET.get('classroom') or request.POST.get('classroom')
    selected = ClassRoom.objects.filter(pk=classroom_id).first() if classroom_id else ClassRoom.objects.first()
    students = selected.students.select_related('user').all() if selected else []

    if request.method == 'POST':
        classroom = get_object_or_404(ClassRoom, pk=request.POST.get('classroom'))
        try:
            day = date.fromisoformat(request.POST.get('date'))
        except (TypeError, ValueError):
            day = date.today()

        for student in classroom.students.select_related('user').all():
            status = request.POST.get(f'status_{student.user_id}', 'absent')
            entry, created = AttendanceEntry.objects.get_or_create(
                classroom=classroom, student=student.user, date=day,
                defaults={'status': status},
            )
            if not created:
                entry.status = status
                entry.save(update_fields=['status'])
            if status == 'present':
                award_points(student, 5, f'Attendance on {day}')
            elif status == 'late':
                award_points(student, 2, f'Late attendance on {day}')

        messages.success(request, 'Attendance saved.')
        return redirect('classroom:attendance')

    return render(request, 'classroom/attendance.html', {
        'classrooms': teachers, 'selected': selected, 'students': students, 'today': date.today(),
    })


@login_required(login_url='login')
def quizzes_view(request):
    attempted = QuizAttempt.objects.filter(profile=_profile_for(request.user)).values_list('quiz_id', flat=True)
    quizzes = Quiz.objects.prefetch_related('questions').all()
    return render(request, 'classroom/quizzes.html', {'quizzes': quizzes, 'attempted': set(attempted)})


@login_required(login_url='login')
def quiz_take(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    profile = _profile_for(request.user)

    if QuizAttempt.objects.filter(profile=profile, quiz=quiz).exists():
        messages.info(request, 'You already took this quiz.')
        return redirect('classroom:quizzes')

    questions = list(quiz.questions.all())

    if request.method == 'POST':
        score = 0
        for q in questions:
            given = request.POST.get(f'q_{q.id}', '').strip().lower()
            if given == q.answer.strip().lower():
                score += 1

        total = len(questions)
        earned = round(quiz.reward_points * (score / total)) if total else 0
        QuizAttempt.objects.create(profile=profile, quiz=quiz, score=score, total=total, points_earned=earned)
        if earned:
            award_points(profile, earned, f'Quiz: {quiz.title}')
        return render(request, 'classroom/quiz_result.html', {
            'quiz': quiz, 'score': score, 'total': total, 'earned': earned,
        })

    return render(request, 'classroom/quiz_take.html', {'quiz': quiz, 'questions': questions})


@login_required(login_url='login')
def assignments_view(request):
    assignments = Assignment.objects.select_related('classroom').all()
    submitted = Submission.objects.filter(student=request.user).values_list('assignment_id', flat=True)
    return render(request, 'classroom/assignments.html', {'assignments': assignments, 'submitted': set(submitted)})


@login_required(login_url='login')
@require_POST
def submit_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    submission, created = Submission.objects.get_or_create(assignment=assignment, student=request.user)
    if created:
        award_points(_profile_for(request.user), 10, f'Submitted: {assignment.title}')
        messages.success(request, 'Assignment submitted! +10 XP')
    else:
        messages.info(request, 'Already submitted.')
    return redirect('classroom:assignments')


@login_required(login_url='login')
def rewards_view(request):
    profile = _profile_for(request.user)
    rewards = Reward.objects.all()

    if request.method == 'POST':
        reward = get_object_or_404(Reward, pk=request.POST.get('reward'))
        if profile.points >= reward.cost:
            award_points(profile, -reward.cost, f'Redeemed: {reward.name}')
            Redemption.objects.create(profile=profile, reward=reward)
            messages.success(request, f'You redeemed {reward.name}!')
        else:
            messages.error(request, 'Not enough points.')
        return redirect('classroom:rewards')

    redemptions = profile.redemptions.select_related('reward').all()[:10]
    return render(request, 'classroom/rewards.html', {
        'profile': profile, 'rewards': rewards, 'redemptions': redemptions,
    })
