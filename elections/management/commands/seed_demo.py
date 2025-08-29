from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime

from django.contrib.auth import get_user_model
from elections.models import Election, Candidate, VoterStatus, Vote
from elections.utils.crypto import encrypt_vote


class Command(BaseCommand):
    help = 'Seed demo data: admin, two voters, an election, two candidates, and cast demo votes.'

    def handle(self, *args, **options):
        User = get_user_model()
        # admin
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'AdminPass123')
            self.stdout.write('Created admin user: admin / AdminPass123')
        else:
            self.stdout.write('Admin user exists')

        # election
        now = timezone.now()
        election, created = Election.objects.get_or_create(
            title='Demo Election',
            defaults={
                'description': 'Demo election seeded by seed_demo',
                'start_time': now - datetime.timedelta(days=1),
                'end_time': now + datetime.timedelta(days=1),
            },
        )
        if created:
            self.stdout.write('Created Demo Election')
        else:
            self.stdout.write('Demo Election exists')

        # candidates
        alice, _ = Candidate.objects.get_or_create(election=election, name='Alice', defaults={'bio': 'Candidate Alice'})
        bob, _ = Candidate.objects.get_or_create(election=election, name='Bob', defaults={'bio': 'Candidate Bob'})
        self.stdout.write('Ensured candidates Alice and Bob')

        # voters
        voters = [('voter1', 'v1@example.com', 'VoterPass1'), ('voter2', 'v2@example.com', 'VoterPass2')]
        for username, email, pw in voters:
            user, created = User.objects.get_or_create(username=username, defaults={'email': email})
            if created:
                user.set_password(pw)
                user.save()
                self.stdout.write(f'Created voter {username} / {pw}')
            VoterStatus.objects.get_or_create(user=user, election=election)

        # cast demo votes if none exist
        if Vote.objects.filter(election=election).count() == 0:
            Vote.objects.create(election=election, encrypted_vote_data=encrypt_vote(str(alice.id), associated_data=str(election.id)))
            Vote.objects.create(election=election, encrypted_vote_data=encrypt_vote(str(bob.id), associated_data=str(election.id)))
            # mark voters as voted
            for username, _, _ in voters:
                user = User.objects.get(username=username)
                vs = VoterStatus.objects.get(user=user, election=election)
                vs.has_voted = True
                vs.save()
            self.stdout.write('Cast demo votes for Alice and Bob')
        else:
            self.stdout.write('Votes already exist; skipping casting')
