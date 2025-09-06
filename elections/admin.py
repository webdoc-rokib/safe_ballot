from django.contrib import admin
from .models import Profile, Election, Candidate, Vote, VoterStatus, Feedback

admin.site.register(Profile)
admin.site.register(Election)
admin.site.register(Candidate)
admin.site.register(Vote)
admin.site.register(VoterStatus)
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
	list_display = ('subject', 'name', 'email', 'created_at', 'user')
	search_fields = ('subject', 'name', 'email', 'message')
	list_filter = ('created_at',)
