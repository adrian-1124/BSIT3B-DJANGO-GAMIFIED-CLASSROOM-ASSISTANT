from django import forms

from .models import AIProvider, Assignment, Badge, ClassRoom, Reward


class BadgeForm(forms.ModelForm):
    class Meta:
        model = Badge
        fields = ['name', 'description', 'icon', 'points_required']


class RewardForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = ['name', 'description', 'cost']


class ClassRoomForm(forms.ModelForm):
    class Meta:
        model = ClassRoom
        fields = ['name', 'section']


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['classroom', 'title', 'description', 'due_date', 'points']
        widgets = {'due_date': forms.DateInput(attrs={'type': 'date'})}


class AIQuizForm(forms.Form):
    TOPIC_SUGGESTIONS = [
        'math', 'science', 'english', 'history', 'geography',
        'programming', 'physics', 'chemistry', 'biology',
        'filipino', 'health', 'economics',
    ]
    classroom = forms.ModelChoiceField(queryset=ClassRoom.objects.all())
    title = forms.CharField(max_length=150)
    topic = forms.CharField(
        max_length=100,
        help_text='Type any topic, e.g. "photosynthesis", "quadratic equations", "Philippine heroes".',
    )
    difficulty = forms.ChoiceField(
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        initial='medium',
    )
    grade_level = forms.CharField(max_length=50, required=False, help_text='Optional, e.g. "Grade 7".')
    count = forms.IntegerField(min_value=1, max_value=10, initial=5)
    reward_points = forms.IntegerField(min_value=1, initial=20)


class AIStudyForm(forms.Form):
    topic = forms.CharField(max_length=100, help_text='What do you want to learn?')


class AIAssignmentForm(forms.Form):
    classroom = forms.ModelChoiceField(queryset=ClassRoom.objects.all())
    topic = forms.CharField(max_length=100)


class AIProviderForm(forms.ModelForm):
    class Meta:
        model = AIProvider
        fields = ['api_key', 'model_name', 'enabled']
        widgets = {'api_key': forms.PasswordInput(render_value=True)}
