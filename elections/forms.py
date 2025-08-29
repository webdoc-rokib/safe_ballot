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
