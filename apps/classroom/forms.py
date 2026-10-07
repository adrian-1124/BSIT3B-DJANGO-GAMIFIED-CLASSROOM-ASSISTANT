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
    classroom = forms.ModelChoiceField(queryset=ClassRoom.objects.all())
    title = forms.CharField(max_length=150)
    topic = forms.ChoiceField(choices=[('math', 'Math'), ('science', 'Science'), ('english', 'English'), ('history', 'History')])
    count = forms.IntegerField(min_value=1, max_value=5, initial=5)
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
