from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .forms import RegistrationForm
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Election, Candidate, Vote, VoterStatus
from .forms import VoteForm
from .utils.crypto import encrypt_vote, decrypt_vote
from .forms import ElectionForm, VoterUploadForm
from .forms import CandidateForm
from datetime import datetime, timezone as _timezone
import csv
from io import TextIOWrapper
from django.http import HttpResponse
import io
import json


def index(request):
    # show currently active elections
    now = timezone.now()
    elections = Election.objects.filter(start_time__lte=now, end_time__gte=now)
    return render(request, 'index.html', {'elections': elections})


def about(request):
    """Static about page describing the project and contact info."""
    return render(request, 'about.html')


def user_logout(request):
    # only allow POST logout to avoid CSRF-sensitive GETs
    if request.method != 'POST':
        return HttpResponseRedirect('/')
    logout(request)
    messages.info(request, 'You have been signed out')
    return redirect('index')


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(username=data['username'], password=data['password1'], email=data.get('email') or '')
            user.first_name = data.get('first_name', '')
            user.last_name = data.get('last_name', '')
            user.save()
            # create profile
            Profile.objects.create(user=user, phone=data.get('phone', ''), role='voter')
            login(request, user)
            return redirect('voter_dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # redirect admins to admin dashboard
            try:
                is_admin = user.is_superuser or user.is_staff or user.profile.role == 'admin'
            except Exception:
                is_admin = False
            if is_admin:
                return redirect('admin_dashboard')
            return redirect('voter_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


@login_required
def voter_dashboard(request):
    # list elections the user is eligible for
    statuses = VoterStatus.objects.filter(user=request.user)
    return render(request, 'voter_dashboard.html', {'statuses': statuses})


@login_required
def vote_view(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    try:
        status = VoterStatus.objects.get(user=request.user, election=election)
    except VoterStatus.DoesNotExist:
        return HttpResponseForbidden('You are not eligible to vote in this election')
    if status.has_voted:
        return HttpResponse('You have already voted in this election')
    if not (election.start_time <= timezone.now() <= election.end_time):
        return HttpResponse('Election is not active')

    candidates = election.candidates.all()
    if request.method == 'POST':
        form = VoteForm(request.POST)
        if form.is_valid():
            candidate_id = form.cleaned_data['candidate_id']
            # encrypt and save vote, bind ciphertext to election id
            ct = encrypt_vote(f'candidate:{candidate_id}', associated_data=str(election.id))
            Vote.objects.create(election=election, encrypted_vote_data=ct)
            status.has_voted = True
            status.save()
            return render(request, 'vote_success.html', {'election': election})
    else:
        form = VoteForm()
    return render(request, 'vote.html', {'election': election, 'candidates': candidates, 'form': form})


def results_view(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    # Allow results to be viewed when election has concluded OR has been published
    if not (timezone.now() >= election.end_time or election.status == 'concluded'):
        return HttpResponseForbidden('Results are not available until election has concluded or published by an admin')

    votes = election.votes.all()
    decrypted = [decrypt_vote(v.encrypted_vote_data, associated_data=str(election.id)) for v in votes]
    # simple aggregation
    tally = {}
    total_votes = 0
    for d in decrypted:
        tally[d] = tally.get(d, 0) + 1
        total_votes += 1

    # compute per-candidate percentages and determine winner(s)
    percentages = {}
    for choice, count in tally.items():
        pct = (count / total_votes * 100) if total_votes > 0 else 0
        percentages[choice] = round(pct, 2)

    if tally:
        max_votes = max(tally.values())
        winners = [c for c, v in tally.items() if v == max_votes]
    else:
        winners = []

    # Build a results list for template consumption and map candidate tokens to names
    results_list = []
    for choice, count in tally.items():
        display = choice
        # if vote stored as 'candidate:<id>' map to candidate name when possible
        if isinstance(choice, str) and choice.startswith('candidate:'):
            try:
                cid = int(choice.split(':', 1)[1])
                cand = Candidate.objects.filter(id=cid, election=election).first()
                if cand:
                    display = cand.name
            except Exception:
                pass
        results_list.append({
            'choice': display,
            'raw_choice': choice,
            'count': count,
            'percentage': percentages.get(choice, 0),
        })

    # prepare chart data JSON
    labels = list(tally.keys())
    values = [tally[k] for k in labels]
    chart_labels_json = json.dumps(labels)
    chart_values_json = json.dumps(values)
    # total eligible voters for this election
    from .models import VoterStatus
    total_voters = VoterStatus.objects.filter(election=election).count()
    casting_percentage = round((total_votes / total_voters * 100), 2) if total_voters > 0 else 0

    # compute winning margin (difference between top and second place)
    margin_votes = 0
    margin_percentage = 0
    if winners and total_votes > 0 and len(tally) > 0:
        if len(winners) == 1:
            # find runner-up
            sorted_counts = sorted(tally.values(), reverse=True)
            top = sorted_counts[0]
            second = sorted_counts[1] if len(sorted_counts) > 1 else 0
            margin_votes = top - second
            margin_percentage = round((margin_votes / total_votes * 100), 2) if total_votes > 0 else 0
        else:
            # tie -> zero margin
            margin_votes = 0
            margin_percentage = 0

    # prepare human-friendly winner names for the template
    winners_display = []
    for w in winners:
        wd = w
        if isinstance(w, str) and w.startswith('candidate:'):
            try:
                cid = int(w.split(':', 1)[1])
                cand = Candidate.objects.filter(id=cid, election=election).first()
                if cand:
                    wd = cand.name
            except Exception:
                pass
        winners_display.append(wd)

    return render(request, 'results.html', {
        'election': election,
        'tally': tally,
        'results_list': results_list,
        'percentages': percentages,
        'total_votes': total_votes,
        'winners': winners,
        'winners_display': winners_display,
        'total_voters': total_voters,
        'casting_percentage': casting_percentage,
        'margin_votes': margin_votes,
        'margin_percentage': margin_percentage,
        'chart_labels_json': chart_labels_json,
        'chart_values_json': chart_values_json,
    })


@login_required
def export_results_csv(request, election_id):
    # export decrypted results as CSV (admin or public after conclusion)
    election = get_object_or_404(Election, pk=election_id)
    if timezone.now() < election.end_time:
        return HttpResponseForbidden('Results are not available until election has concluded')
    votes = election.votes.all()
    decrypted = [decrypt_vote(v.encrypted_vote_data, associated_data=str(election.id)) for v in votes]
    tally = {}
    for d in decrypted:
        tally[d] = tally.get(d, 0) + 1

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['choice', 'count'])
    for choice, count in tally.items():
        writer.writerow([choice, count])
    resp = HttpResponse(buffer.getvalue(), content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="results_{election.id}.csv"'
    return resp


def _is_admin(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    # Superusers and staff are admins
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True
    try:
        return user.profile.role == 'admin'
    except Exception:
        return False


@login_required
def admin_dashboard(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    elections = Election.objects.all()
    return render(request, 'admin_dashboard.html', {'elections': elections})


@login_required
def create_election(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    if request.method == 'POST':
        form = ElectionForm(request.POST)
        if form.is_valid():
            # prefer client-provided UTC ISO fields if present (created by JS)
            def parse_utc_field(name, default_dt):
                v = request.POST.get(name)
                if not v:
                    return default_dt
                try:
                    # handle trailing Z
                    if v.endswith('Z'):
                        v2 = v[:-1]
                        dt = datetime.fromisoformat(v2)
                        return dt.replace(tzinfo=_timezone.utc)
                    dt = datetime.fromisoformat(v)
                    if dt.tzinfo is None:
                        return dt.replace(tzinfo=_timezone.utc)
                    return dt
                except Exception:
                    return default_dt

            s = parse_utc_field('start_time_utc', form.cleaned_data['start_time'])
            e = parse_utc_field('end_time_utc', form.cleaned_data['end_time'])
            Election.objects.create(
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                start_time=s,
                end_time=e,
            )
            return redirect('admin_dashboard')
    else:
        form = ElectionForm()
    return render(request, 'create_election.html', {'form': form})


@login_required
def edit_election(request, election_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    if request.method == 'POST':
        form = ElectionForm(request.POST)
        if form.is_valid():
            # prefer client-provided UTC ISO fields if present
            def parse_utc_field(name, default_dt):
                v = request.POST.get(name)
                if not v:
                    return default_dt
                try:
                    if v.endswith('Z'):
                        v2 = v[:-1]
                        dt = datetime.fromisoformat(v2)
                        return dt.replace(tzinfo=_timezone.utc)
                    dt = datetime.fromisoformat(v)
                    if dt.tzinfo is None:
                        return dt.replace(tzinfo=_timezone.utc)
                    return dt
                except Exception:
                    return default_dt

            election.title = form.cleaned_data['title']
            election.description = form.cleaned_data['description']
            election.start_time = parse_utc_field('start_time_utc', form.cleaned_data['start_time'])
            election.end_time = parse_utc_field('end_time_utc', form.cleaned_data['end_time'])
            election.save()
            return redirect('admin_dashboard')
    else:
        form = ElectionForm(initial={
            'title': election.title,
            'description': election.description,
            'start_time': election.start_time,
            'end_time': election.end_time,
        })
    return render(request, 'create_election.html', {'form': form, 'election': election})


@login_required
def delete_election(request, election_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    if request.method == 'POST':
        election.delete()
        return redirect('admin_dashboard')
    return render(request, 'confirm_delete.html', {'object': election, 'type': 'election'})


@login_required
def publish_results(request, election_id):
    """Mark an election as concluded (publish results).
    This is a simple admin action -- it sets status='concluded'.
    Only accessible to admins (staff, superuser, or profile.role == 'admin').
    """
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    if request.method == 'POST':
        election.status = 'concluded'
        election.save()
        return redirect('admin_dashboard')
    # For safety, show a confirmation page
    return render(request, 'confirm_delete.html', {'object': election, 'type': 'publish'})


@login_required
def upload_voters(request, election_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    if request.method == 'POST':
        form = VoterUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = TextIOWrapper(request.FILES['csv_file'].file, encoding='utf-8')
            reader = csv.DictReader(f)
            imported = 0
            from django.contrib.auth.models import User
            for row in reader:
                username = row.get('username')
                if not username:
                    continue
                try:
                    user = User.objects.get(username=username)
                    VoterStatus.objects.get_or_create(user=user, election=election)
                    imported += 1
                except User.DoesNotExist:
                    continue
            return render(request, 'upload_result.html', {'imported': imported, 'election': election})
    else:
        form = VoterUploadForm()
    return render(request, 'upload_voters.html', {'form': form, 'election': election})


@login_required
def create_candidate(request, election_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    if request.method == 'POST':
        form = CandidateForm(request.POST)
        if form.is_valid():
            Candidate.objects.create(
                election=election,
                name=form.cleaned_data['name'],
                bio=form.cleaned_data['bio'],
                photo=form.cleaned_data['photo'] or None,
            )
            return redirect('admin_dashboard')
    else:
        form = CandidateForm()
    return render(request, 'create_candidate.html', {'form': form, 'election': election})


@login_required
def list_candidates(request, election_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    candidates = election.candidates.all()
    # secure decrypt-and-aggregate per candidate
    tally = {c.id: 0 for c in candidates}
    votes = election.votes.all()
    for v in votes:
        try:
            plaintext = decrypt_vote(v.encrypted_vote_data, associated_data=str(election.id))
        except Exception:
            # skip votes that can't be decrypted (missing key / tampered)
            continue
        if isinstance(plaintext, bytes):
            try:
                plaintext = plaintext.decode('utf-8')
            except Exception:
                continue
        # expected format: 'candidate:<id>'
        if not isinstance(plaintext, str):
            continue
        if plaintext.startswith('candidate:'):
            try:
                cid = int(plaintext.split(':', 1)[1])
            except Exception:
                continue
            tally[cid] = tally.get(cid, 0) + 1
    return render(request, 'list_candidates.html', {'election': election, 'candidates': candidates, 'tally': tally})


@login_required
def edit_candidate(request, election_id, candidate_id):
    if not _is_admin(request.user):
        messages.error(request, 'Admins only: you do not have permission to perform that action')
        return redirect('index')
    candidate = get_object_or_404(Candidate, pk=candidate_id, election__id=election_id)
    if request.method == 'POST':
        form = CandidateForm(request.POST)
        if form.is_valid():
            candidate.name = form.cleaned_data['name']
            candidate.bio = form.cleaned_data['bio']
            # photo handling skipped for brevity
            candidate.save()
            return redirect('list_candidates', election_id=election_id)
    else:
        form = CandidateForm(initial={'name': candidate.name, 'bio': candidate.bio})
    return render(request, 'create_candidate.html', {'form': form, 'election': candidate.election, 'candidate': candidate})


@login_required
def delete_candidate(request, election_id, candidate_id):
    if not _is_admin(request.user):
        messages.error(request, 'Admins only: you do not have permission to perform that action')
        return redirect('index')
    candidate = get_object_or_404(Candidate, pk=candidate_id, election__id=election_id)
    if request.method == 'POST':
        candidate.delete()
        return redirect('list_candidates', election_id=election_id)
    return render(request, 'confirm_delete.html', {'object': candidate, 'type': 'candidate'})
