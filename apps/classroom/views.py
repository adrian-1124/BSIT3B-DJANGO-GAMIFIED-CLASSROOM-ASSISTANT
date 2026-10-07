from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .models import (
    Assignment, AttendanceEntry, Badge, ClassRoom, Question, Quiz,
    QuizAttempt, Redemption, Reward, StudentProfile, Submission,
)
from .services import award_points, touch_streak
from .forms import (
    AIQuizForm, AIStudyForm, AIAssignmentForm, AIProviderForm,
    AssignmentForm, BadgeForm, ClassRoomForm, RewardForm,
)

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

    show_confetti = request.session.pop('show_confetti', False)

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
        'show_confetti': show_confetti,
    })


@login_required(login_url='login')
@require_POST
def daily_bonus(request):
    from datetime import date
    profile = _profile_for(request.user)
    if profile.last_bonus_date != date.today():
        award_points(profile, 5, 'Daily star bonus')
        profile.last_bonus_date = date.today()
        profile.save(update_fields=['last_bonus_date'])
        request.session['show_confetti'] = True
        messages.success(request, '⭐ Daily Star Bonus: +5 XP!')
    else:
        messages.info(request, 'You already claimed today\'s star bonus.')
    return redirect('classroom:dashboard')


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
            checked = request.POST.getlist(f'status_{student.user_id}')
            for choice in ('present', 'late', 'excused', 'absent'):
                if choice in checked:
                    status = choice
                    break
            else:
                status = 'absent'
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
            # absent / excused award no points

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
        messages.info(request, 'You already took this quiz — showing your answers.')
        return redirect('classroom:quiz_review', pk=quiz.pk)

    questions = list(quiz.questions.all())

    if request.method == 'POST':
        score = 0
        given_answers = {}
        for q in questions:
            given = request.POST.get(f'q_{q.id}', '').strip()
            given_answers[str(q.id)] = given
            if given.lower() == q.answer.strip().lower():
                score += 1

        total = len(questions)
        earned = round(quiz.reward_points * (score / total)) if total else 0
        QuizAttempt.objects.create(profile=profile, quiz=quiz, score=score, total=total, points_earned=earned, answers=given_answers)
        if earned:
            award_points(profile, earned, f'Quiz: {quiz.title}')
        from .ai import ai_quiz_feedback
        feedback, feedback_provider = ai_quiz_feedback(quiz.title, score, total)
        return render(request, 'classroom/quiz_result.html', {
            'quiz': quiz, 'score': score, 'total': total, 'earned': earned,
            'feedback': feedback, 'feedback_provider': feedback_provider,
        })

    return render(request, 'classroom/quiz_take.html', {'quiz': quiz, 'questions': questions})


@login_required(login_url='login')
def quiz_review(request, pk):
    """Review a completed quiz: correct answers vs the student's answers."""
    quiz = get_object_or_404(Quiz, pk=pk)
    profile = _profile_for(request.user)
    attempt = get_object_or_404(QuizAttempt, profile=profile, quiz=quiz)
    given = attempt.answers or {}
    rows = []
    for q in quiz.questions.all():
        student_answer = given.get(str(q.id), '')
        rows.append({
            'question': q,
            'student_answer': student_answer,
            'is_correct': (student_answer or '').strip().lower() == q.answer.strip().lower(),
        })
    return render(request, 'classroom/quiz_review.html', {
        'quiz': quiz, 'attempt': attempt, 'rows': rows,
    })


@login_required(login_url='login')
@require_POST
def quiz_retake(request, pk):
    """Delete the old attempt (reversing its XP) so the quiz can be retaken.

    Needed for attempts made before answers were recorded — retaking
    stores the answers so the review page shows them afterwards.
    """
    quiz = get_object_or_404(Quiz, pk=pk)
    profile = _profile_for(request.user)
    attempt = get_object_or_404(QuizAttempt, profile=profile, quiz=quiz)
    if attempt.points_earned:
        award_points(profile, -attempt.points_earned, f'Quiz retake reset: {quiz.title}')
    attempt.delete()
    messages.info(request, f'Attempt cleared — you can now retake "{quiz.title}".')
    return redirect('classroom:quiz_take', pk=quiz.pk)


@login_required(login_url='login')
def assignments_view(request):
    assignments = Assignment.objects.select_related('classroom').all()
    my_submissions = {s.assignment_id: s for s in Submission.objects.filter(student=request.user)}
    return render(request, 'classroom/assignments.html', {
        'assignments': assignments,
        'submitted': set(my_submissions.keys()),
        'my_submissions': my_submissions,
    })


@login_required(login_url='login')
@require_POST
def submit_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    uploaded = request.FILES.get('file')
    submission, created = Submission.objects.get_or_create(assignment=assignment, student=request.user)
    if uploaded:
        submission.file = uploaded
        submission.save(update_fields=['file'])
    if created:
        award_points(_profile_for(request.user), 10, f'Submitted: {assignment.title}')
        messages.success(request, 'Assignment submitted! +10 XP')
    elif uploaded:
        messages.success(request, 'File attached to your submission.')
    else:
        messages.info(request, 'Already submitted.')
    return redirect('classroom:assignments')


@login_required(login_url='login')
def rewards_view(request):
    from django.db.models import Count, Q
    profile = _profile_for(request.user)
    rewards = Reward.objects.annotate(
        my_redemptions=Count('redemption', filter=Q(redemption__profile=profile)),
    ).order_by('cost')

    if request.method == 'POST':
        reward = get_object_or_404(Reward, pk=request.POST.get('reward'))
        if profile.points >= reward.cost:
            award_points(profile, -reward.cost, f'Redeemed: {reward.name}')
            redemption = Redemption.objects.create(profile=profile, reward=reward)
            request.session['just_redeemed'] = {
                'reward': reward.name,
                'description': reward.description,
                'cost': reward.cost,
                'id': redemption.pk,
            }
            messages.success(request, f'You redeemed {reward.name}!')
        else:
            messages.error(request, 'Not enough points.')
        return redirect('classroom:rewards')

    just_redeemed = request.session.pop('just_redeemed', None)
    redemptions = profile.redemptions.select_related('reward').all()[:20]
    return render(request, 'classroom/rewards.html', {
        'profile': profile, 'rewards': rewards, 'redemptions': redemptions,
        'just_redeemed': just_redeemed,
    })


# ---------------------------------------------------------------------------
# Admin / Staff management (CRUD pages)
# ---------------------------------------------------------------------------

@teacher_required
def staff_dashboard(request):
    return render(request, 'classroom/staff.html', {
        'badge_count': Badge.objects.count(),
        'reward_count': Reward.objects.count(),
        'class_count': ClassRoom.objects.count(),
        'assignment_count': Assignment.objects.count(),
        'quiz_count': Quiz.objects.count(),
    })


def _staff_crud(request, model, form_class, title):
    editing_pk = request.GET.get('edit') or request.POST.get('edit_pk')
    editing = model.objects.filter(pk=editing_pk).first() if editing_pk else None

    if request.method == 'POST':
        if request.POST.get('delete'):
            obj = get_object_or_404(model, pk=request.POST['delete'])
            obj.delete()
            messages.success(request, f'{title} item deleted.')
            return redirect(request.path_info)

        form = form_class(request.POST, instance=editing)
        if form.is_valid():
            obj = form.save(commit=False)
            if model is ClassRoom and not obj.teacher_id:
                obj.teacher = request.user
            obj.save()
            messages.success(request, f'{title} saved.')
            return redirect(request.path_info)
    else:
        form = form_class(instance=editing)

    return render(request, 'classroom/staff_crud.html', {
        'objects': model.objects.all(), 'form': form, 'title': title, 'editing': editing,
    })


@teacher_required
def staff_badges(request):
    return _staff_crud(request, Badge, BadgeForm, 'Badges')


@teacher_required
def staff_rewards(request):
    return _staff_crud(request, Reward, RewardForm, 'Rewards')


@teacher_required
def staff_classrooms(request):
    return _staff_crud(request, ClassRoom, ClassRoomForm, 'Classrooms')


@teacher_required
def staff_assignments(request):
    return _staff_crud(request, Assignment, AssignmentForm, 'Assignments')


@teacher_required
def ai_quiz(request):
    if request.method == 'POST':
        form = AIQuizForm(request.POST)
        if form.is_valid():
            from .ai import ai_generate_quiz_questions
            quiz = Quiz.objects.create(
                classroom=form.cleaned_data['classroom'],
                title=form.cleaned_data['title'],
                reward_points=form.cleaned_data['reward_points'],
            )
            items, provider = ai_generate_quiz_questions(
                form.cleaned_data['topic'], form.cleaned_data['count'])
            for text, answer in items:
                Question.objects.create(quiz=quiz, text=text, answer=answer)
            messages.success(
                request,
                f'AI generated quiz "{quiz.title}" with {quiz.questions.count()} '
                f'questions (via {provider}).')
            return redirect('classroom:quizzes')
    else:
        form = AIQuizForm()
    return render(request, 'classroom/ai_quiz.html', {'form': form})


@login_required(login_url='login')
def ai_study(request):
    """Student AI study assistant: topic in, study guide out."""
    from .ai import ai_study_guide
    guide, provider, topic = None, None, ''
    if request.method == 'POST':
        form = AIStudyForm(request.POST)
        if form.is_valid():
            topic = form.cleaned_data['topic']
            guide, provider = ai_study_guide(topic)
    else:
        form = AIStudyForm()
    return render(request, 'classroom/ai_study.html', {
        'form': form, 'guide': guide, 'provider': provider, 'topic': topic,
    })


@teacher_required
def ai_assignment(request):
    """Teacher AI assignment generator: topic in, Assignment row out."""
    from .ai import ai_assignment_idea
    if request.method == 'POST':
        form = AIAssignmentForm(request.POST)
        if form.is_valid():
            classroom = form.cleaned_data['classroom']
            topic = form.cleaned_data['topic']
            idea, provider = ai_assignment_idea(topic, str(classroom))
            assignment = Assignment.objects.create(
                classroom=classroom, title=idea['title'][:150],
                description=idea['description'], points=idea['points'],
            )
            messages.success(
                request,
                f'AI created assignment "{assignment.title}" (via {provider}).')
            return redirect('classroom:assignments')
    else:
        form = AIAssignmentForm()
    return render(request, 'classroom/ai_assignment.html', {'form': form})


@teacher_required
def ai_insights(request):
    """Teacher AI class insights: stats in, teaching tips out."""
    from django.db.models import Avg
    from .ai import ai_class_insights
    from .models import AILog

    total_students = StudentProfile.objects.count()
    avg_xp = StudentProfile.objects.aggregate(a=Avg('xp'))['a'] or 0
    top = StudentProfile.objects.select_related('user').order_by('-xp')[:3]
    inactive = StudentProfile.objects.filter(xp=0).count()
    stats_text = (
        f'Students: {total_students}. Average XP: {round(avg_xp)}. '
        f'Inactive (0 XP): {inactive}. '
        f'Top 3: {", ".join(f"{p.user.username} ({p.xp} XP)" for p in top) or "none"}. '
        f'Quizzes: {Quiz.objects.count()}. Assignments: {Assignment.objects.count()}.'
    )
    insights, provider = None, None
    if request.method == 'POST':
        insights, provider = ai_class_insights(stats_text)
    logs = AILog.objects.all()[:10]
    return render(request, 'classroom/ai_insights.html', {
        'stats_text': stats_text, 'insights': insights, 'provider': provider, 'logs': logs,
    })


@teacher_required
def ai_settings(request):
    """Manage AI provider API keys (stored in DB, override .env)."""
    from .ai import provider_status
    from .models import AIProvider
    for name in ('openrouter', 'gemini'):
        AIProvider.objects.get_or_create(name=name, defaults={'enabled': True})
    providers = AIProvider.objects.all().order_by('name')

    if request.method == 'POST':
        pk = request.POST.get('provider_id')
        obj = get_object_or_404(AIProvider, pk=pk)
        form = AIProviderForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'{obj.name} API settings saved.')
            return redirect('classroom:ai_settings')
    else:
        form = None
    editing_pk = request.GET.get('edit')
    editing = AIProvider.objects.filter(pk=editing_pk).first() if editing_pk else None
    return render(request, 'classroom/ai_settings.html', {
        'providers': providers, 'status': provider_status(), 'editing': editing,
    })


@login_required(login_url='login')
def ai_architecture(request):
    """Visible AI automation architecture page."""
    from .ai import provider_status
    from .models import AILog
    return render(request, 'classroom/ai_architecture.html', {
        'status': provider_status(), 'logs': AILog.objects.all()[:10],
    })
