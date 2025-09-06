from django import forms

class VoteForm(forms.Form):
    candidate_id = forms.IntegerField()


class ElectionForm(forms.Form):
    title = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6}), required=False)
    start_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    end_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))


class VoterUploadForm(forms.Form):
    csv_file = forms.FileField(help_text='CSV with header: username', widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))


class CandidateForm(forms.Form):
    name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}), required=False)
    photo = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))



class PublishKeyRotateForm(forms.Form):
    current_key = forms.CharField(
        max_length=64,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current publish key'}),
        label='Current key'
    )
    new_key = forms.CharField(
        max_length=64,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New publish key'}),
        label='New key'
    )
    confirm_new_key = forms.CharField(
        max_length=64,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new publish key'}),
        label='Confirm new key'
    )
    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_key') != cleaned.get('confirm_new_key'):
            raise forms.ValidationError('New keys do not match')
        return cleaned


class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=150, label='Username', widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='Confirm password')
    first_name = forms.CharField(max_length=30, required=False, label='First name', widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, label='Last name', widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, label='Email', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=20, required=False, label='Phone', widget=forms.TextInput(attrs={'class': 'form-control'}))
    agree_policies = forms.BooleanField(required=True, label='I agree to the Privacy Policy, Terms of Use, and Data Policy')

    def clean_username(self):
        u = self.cleaned_data.get('username')
        from django.contrib.auth.models import User
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError('A user with that username already exists')
        return u

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match')
        return cleaned


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your message...'}))
