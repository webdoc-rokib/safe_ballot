# Cleaned tests module: moved all runtime code into setUp/test methods and removed stray top-level statements
import os
os.environ.setdefault('AES_KEY_HEX', '00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff')
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from elections.models import Election, Candidate, Vote, VoterStatus
from elections.utils.crypto import encrypt_vote, decrypt_vote
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
import datetime


class CryptoTests(TestCase):
    def test_encrypt_decrypt(self):
        plaintext = 'candidate:42'
        ct = encrypt_vote(plaintext)
        self.assertNotEqual(ct, plaintext)
        pt = decrypt_vote(ct)
        self.assertEqual(pt, plaintext)


class VotingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='pass')
        now = timezone.now()
        self.election = Election.objects.create(
            title='Test',
            start_time=now - datetime.timedelta(hours=1),
            end_time=now + datetime.timedelta(hours=1),
            status='active',
        )
        self.candidate = Candidate.objects.create(election=self.election, name='Bob')
        VoterStatus.objects.create(user=self.user, election=self.election, has_voted=False)

    def test_user_can_vote_once(self):
        vs = VoterStatus.objects.get(user=self.user, election=self.election)
        self.assertFalse(vs.has_voted)
        # simulate vote
        ct = encrypt_vote(f'candidate:{self.candidate.id}', associated_data=str(self.election.id))
        Vote.objects.create(election=self.election, encrypted_vote_data=ct)
        vs.has_voted = True
        vs.save()
        vs.refresh_from_db()
        self.assertTrue(vs.has_voted)

    def test_vote_view_encrypts_and_prevents_double_vote(self):
        self.client.login(username='alice', password='pass')
        url = f'/vote/{self.election.id}/'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        r = self.client.post(url, {'candidate_id': self.candidate.id})
        self.assertContains(r, 'Thanks', status_code=200)
        vs = VoterStatus.objects.get(user=self.user, election=self.election)
        self.assertTrue(vs.has_voted)
        # posting again should show already voted
        r = self.client.post(url, {'candidate_id': self.candidate.id})
        self.assertContains(r, 'already voted', status_code=200)

    def test_results_gated_until_end_time(self):
        url = f'/results/{self.election.id}/'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)
        # advance end_time to past
        self.election.end_time = timezone.now() - datetime.timedelta(minutes=1)
        self.election.save()
        # create a vote
        Vote.objects.create(
            election=self.election,
            encrypted_vote_data=encrypt_vote(f'candidate:{self.candidate.id}', associated_data=str(self.election.id)),
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'candidate:')


class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password='pass')
        from elections.models import Profile
        Profile.objects.update_or_create(user=self.admin, defaults={'role': 'admin'})

        self.user = User.objects.create_user('bob', password='pass')
        now = timezone.now()
        self.election = Election.objects.create(
            title='AdminTest',
            start_time=now - datetime.timedelta(hours=1),
            end_time=now + datetime.timedelta(hours=1),
            status='active',
        )

    def test_admin_upload_voters_csv(self):
        self.client.login(username='admin', password='pass')
        csv_content = 'username\n' + self.user.username + '\n'
        upload = SimpleUploadedFile('voters.csv', csv_content.encode('utf-8'), content_type='text/csv')
        url = reverse('upload_voters', args=[self.election.id])
        r = self.client.post(url, {'csv_file': upload}, follow=True)
        self.assertContains(r, 'Imported 1 voters')

    def test_non_admin_cannot_access_admin(self):
        self.client.login(username='bob', password='pass')
        r = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(r.status_code, 403)

    def test_admin_can_create_candidate(self):
        self.client.login(username='admin', password='pass')
        url = reverse('create_candidate', args=[self.election.id])
        r = self.client.post(url, {'name': 'NewCand', 'bio': 'Bio', 'photo': ''}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Candidate.objects.filter(election=self.election, name='NewCand').exists())

    def test_non_admin_cannot_create_candidate(self):
        self.client.login(username='bob', password='pass')
        url = reverse('create_candidate', args=[self.election.id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)


class ExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('eve', password='pass')
        now = timezone.now()
        self.election = Election.objects.create(
            title='ExportTest',
            start_time=now - datetime.timedelta(hours=2),
            end_time=now - datetime.timedelta(hours=1),
            status='concluded',
        )
        self.candidate = Candidate.objects.create(election=self.election, name='Zed')
        Vote.objects.create(
            election=self.election,
            encrypted_vote_data=encrypt_vote(f'candidate:{self.candidate.id}', associated_data=str(self.election.id)),
        )

    def test_export_csv(self):
        self.client.login(username='eve', password='pass')
        url = reverse('export_results_csv', args=[self.election.id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn('choice,count', r.content.decode('utf-8'))
