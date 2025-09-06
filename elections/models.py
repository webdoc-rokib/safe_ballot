from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = [('voter', 'Voter'), ('admin', 'Admin')]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='voter')
    phone = models.CharField(max_length=20, blank=True)
    # email confirmation and admin approval for voter accounts
    is_confirmed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} ({self.role})'

class Election(models.Model):
    STATUS_CHOICES = [('pending','Pending'), ('active','Active'), ('concluded','Concluded')]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    # Owner/creator of the election (used for admin-scoped management)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_elections')
    # One-time publish key (stored as a secure hash); required for admins to publish results.
    publish_key_hash = models.CharField(max_length=128, null=True, blank=True)
    # Audit details for publishing
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='published_elections')
    # Rate limiting for publish key verification
    publish_attempts = models.IntegerField(default=0)
    publish_blocked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class Candidate(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    name = models.CharField(max_length=255)
    bio = models.TextField(blank=True)
    # store candidate photo as ImageField
    photo = models.ImageField(upload_to='candidate_photos/', blank=True, null=True)

    def __str__(self):
        return f'{self.name} — {self.election.title}'

class Vote(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='votes')
    encrypted_vote_data = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Vote for {self.election.title} @ {self.timestamp.isoformat()}'

class VoterStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    has_voted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'election')

    def __str__(self):
        return f'{self.user.username} - {self.election.title} - voted={self.has_voted}'
