from django.contrib import admin
from .models import Profile, Election, Candidate, Vote, VoterStatus

admin.site.register(Profile)
admin.site.register(Election)
admin.site.register(Candidate)
admin.site.register(Vote)
admin.site.register(VoterStatus)
