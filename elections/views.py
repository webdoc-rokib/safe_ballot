from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .forms import RegistrationForm
from .forms import ContactForm
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncHour
from datetime import timedelta
from .models import Election, Candidate, Vote, VoterStatus, Feedback
from .forms import VoteForm
from .utils.crypto import encrypt_vote, decrypt_vote
from .forms import ElectionForm, VoterUploadForm
from .forms import PublishKeyRotateForm
from .forms import CandidateForm
from datetime import datetime, timezone as _timezone
import csv
from io import TextIOWrapper
from django.http import HttpResponse
import io
import json
from django.core import signing
from django.core.mail import send_mail
from django.conf import settings


def index(request):
    # Enhanced home with active/upcoming elections and stats
    now = timezone.now()
    # Auto-sync statuses so pending -> active when start_time passes
    _sync_election_statuses()
    # Active elections with quick metrics, filtered by role
    active_qs = Election.objects.filter(start_time__lte=now, end_time__gte=now)
    if request.user.is_authenticated:
        # Superusers see all
        if getattr(request.user, 'is_superuser', False):
            pass
        else:
            # Admins see only their own; voters only eligible
            try:
                if request.user.profile.role == 'admin':
                    active_qs = active_qs.filter(created_by=request.user)
                else:
                    active_qs = active_qs.filter(voterstatus__user=request.user)
            except Exception:
                active_qs = active_qs.filter(voterstatus__user=request.user)
    else:
        # Anonymous users do not see restricted elections
        active_qs = active_qs.none()

    active = (
        active_qs
        .annotate(
            candidates_count=Count('candidates', distinct=True),
            votes_cast=Count('votes', distinct=True),
        )
        .order_by('end_time')
    )
    # Upcoming elections (role-scoped)
    upcoming_qs = Election.objects.filter(start_time__gt=now)
    if request.user.is_authenticated:
        if getattr(request.user, 'is_superuser', False):
            pass
        else:
            try:
                if request.user.profile.role == 'admin':
                    upcoming_qs = upcoming_qs.filter(created_by=request.user)
                else:
                    upcoming_qs = upcoming_qs.filter(voterstatus__user=request.user)
            except Exception:
                upcoming_qs = upcoming_qs.filter(voterstatus__user=request.user)
    else:
        upcoming_qs = upcoming_qs.none()
    upcoming = upcoming_qs.order_by('start_time')[:6]

    # Recently concluded (role-scoped)
    concluded_qs = Election.objects.filter(status='concluded')
    if request.user.is_authenticated:
        if getattr(request.user, 'is_superuser', False):
            pass
        else:
            try:
                if request.user.profile.role == 'admin':
                    concluded_qs = concluded_qs.filter(created_by=request.user)
                else:
                    concluded_qs = concluded_qs.filter(voterstatus__user=request.user)
            except Exception:
                concluded_qs = concluded_qs.filter(voterstatus__user=request.user)
    else:
        concluded_qs = concluded_qs.none()
    concluded_recent = concluded_qs.order_by('-end_time')[:2]

    # Totals and average turnout across elections with eligible > 0
    total_elections = Election.objects.count()
    total_votes = Vote.objects.count()

    # average turnout: avg(votes/eligible) per election
    turnouts = []
    for e in Election.objects.all():
        eligible = VoterStatus.objects.filter(election=e).count()
        votes_cast = Vote.objects.filter(election=e).count()
        if eligible > 0:
            turnouts.append(votes_cast / eligible)
    avg_turnout_pct = round((sum(turnouts) / len(turnouts) * 100), 2) if turnouts else 0

    context = {
        'elections': active,
        'upcoming': upcoming,
        'concluded_recent': concluded_recent,
        'total_elections': total_elections,
        'total_votes': total_votes,
        'avg_turnout_pct': avg_turnout_pct,
        'now': now,
    }
    return render(request, 'index.html', context)


def about(request):
    """Static about page describing the project and contact info."""
    return render(request, 'about.html')


def privacy_page(request):
    """Render the privacy policy page."""
    return render(request, 'privacy.html')


def terms_page(request):
    """Render the terms of use page."""
    return render(request, 'terms.html')


def data_policy_page(request):
    """Render the data policy page."""
    return render(request, 'data_policy.html')


def how_it_works_page(request):
    return render(request, 'how_it_works.html')


def social_proof_page(request):
    return render(request, 'social_proof.html')


def contact_page(request):
    """Contact/feedback form. Sends an email via configured email backend. Always shows success in dev."""
    sent = False
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            subject = f"[SafeBallot Contact] {cd['subject']}"
            body = f"From: {cd['name']} <{cd['email']}>\n\n{cd['message']}"
            # Persist feedback for admin review regardless of email backend
            try:
                from .models import Feedback
                Feedback.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    name=cd['name'],
                    email=cd['email'],
                    subject=cd['subject'],
                    message=cd['message'],
                )
            except Exception:
                # Fail silently; email path below still attempts notification
                pass
            try:
                # Notify all active superusers with a valid email; fall back to CONTACT_RECEIVER_EMAIL if provided
                superuser_emails = list(
                    User.objects.filter(is_superuser=True, is_active=True)
                    .exclude(email='')
                    .values_list('email', flat=True)
                )
                fallback_email = getattr(settings, 'CONTACT_RECEIVER_EMAIL', None)
                if fallback_email and fallback_email not in superuser_emails:
                    superuser_emails.append(fallback_email)
                recipients = superuser_emails or [fallback_email] if fallback_email else []
                # If no recipients configured, still attempt to send to a neutral address to exercise backend
                if not recipients:
                    recipients = ['noreply@example.com']

                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com',
                    recipients,
                )
                sent = True
                messages.success(request, 'Thanks! Your message has been sent.')
            except Exception:
                # In dev, still show success to avoid exposing config
                messages.info(request, 'Message recorded (dev).')
                sent = True
            form = ContactForm()  # reset form
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form, 'sent': sent})


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
            # create or update profile (unconfirmed and unapproved).
            # A post_save signal may already have created a Profile for this User,
            # so update the existing one instead of blindly creating another.
            try:
                profile = user.profile
                profile.phone = data.get('phone', '')
                profile.role = 'voter'
                profile.is_confirmed = False
                profile.is_approved = False
                profile.save()
            except Profile.DoesNotExist:
                Profile.objects.create(user=user, phone=data.get('phone', ''), role='voter', is_confirmed=False, is_approved=False)

            # generate confirmation token and send email (if email provided)
            email = data.get('email')
            if email:
                token = signing.dumps({'user_id': user.id}, salt='email-confirm')
                confirm_url = request.build_absolute_uri(f"/confirm-email/?token={token}")
                # Use Django email backend; in dev this may print to console or be a no-op
                try:
                    send_mail(
                        subject='Confirm your SafeBallot account',
                        message=f'Please confirm your account by visiting: {confirm_url}',
                        from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com',
                        recipient_list=[email],
                    )
                    messages.info(request, 'A confirmation email has been sent. Check your inbox to confirm your account.')
                except Exception:
                    # fallback: log the URL to the console/messages so an operator can copy it
                    messages.info(request, f'Confirmation URL (dev): {confirm_url}')

            # after registration, show a notice that account requires confirmation and admin approval
            return render(request, 'registration_pending.html', {'email': email})
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def confirm_email(request):
    token = request.GET.get('token')
    if not token:
        return HttpResponse('Missing token', status=400)
    try:
        data = signing.loads(token, salt='email-confirm', max_age=60*60*24)
        uid = data.get('user_id')
        user = User.objects.get(id=uid)
        profile = user.profile
        profile.is_confirmed = True
        profile.save()
        messages.success(request, 'Email confirmed. An admin will approve your account shortly.')
        return redirect('index')
    except signing.SignatureExpired:
        return HttpResponse('Confirmation link has expired', status=400)
    except Exception:
        return HttpResponse('Invalid token', status=400)


@login_required
def admin_pending_users(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    # show unapproved users
    pending = Profile.objects.filter(role='voter', is_approved=False).select_related('user')
    return render(request, 'admin_pending_users.html', {'pending': pending})


@login_required
def admin_approve_user(request, profile_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    profile = get_object_or_404(Profile, pk=profile_id)
    if request.method == 'POST':
        profile.is_approved = True
        profile.save()
        messages.success(request, f'User {profile.user.username} approved')
        return redirect('admin_pending_users')
    return render(request, 'confirm_delete.html', {'object': profile.user, 'type': 'approve'})


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
    # list elections the user is eligible for (voters only)
    now = timezone.now()
    _sync_election_statuses()
    statuses = (
        VoterStatus.objects
        .filter(user=request.user, election__start_time__lte=now, election__end_time__gte=now)
        .select_related('election')
        .order_by('election__end_time')
    )
    return render(request, 'voter_dashboard.html', {'statuses': statuses, 'now': now})


@login_required
def vote_view(request, election_id):
    election = get_object_or_404(Election, pk=election_id)
    # Only eligible voters can vote; admins/superusers cannot cast votes by default
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
    # Results visible when election concluded; visibility scope:
    # - Superusers/staff: all
    # - Admins: their own elections
    # - Voters: only if eligible
    concluded = (timezone.now() >= election.end_time or election.status == 'concluded')
    if not concluded:
        return HttpResponseForbidden('Results are not available until election has concluded')
    user = request.user
    if not user.is_authenticated:
        return HttpResponseForbidden('Sign in to view results')
    if getattr(user, 'is_superuser', False):
        pass
    elif _is_super_or_owner(user, election):
        pass
    else:
        # Voters may view only if eligible for this election
        if not VoterStatus.objects.filter(user=user, election=election).exists():
            return HttpResponseForbidden('You are not eligible to view results for this election')

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
    # Visibility per role
    u = request.user
    if getattr(u, 'is_superuser', False) or _is_super_or_owner(u, election):
        pass
    else:
        if not VoterStatus.objects.filter(user=u, election=election).exists():
            return HttpResponseForbidden('Not allowed to export results for this election')
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


def _is_super_or_owner(user, election: Election) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    # Treat the creator as owner regardless of profile role; outer guards restrict to admins
    return election.created_by_id == user.id


@login_required
def admin_dashboard(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    _sync_election_statuses()
    # Elections with aggregated stats
    base_qs = Election.objects.all()
    # Non-super admins see only their own elections
    if getattr(request.user, 'is_superuser', False):
        elections_qs = base_qs
    else:
        elections_qs = base_qs.filter(created_by=request.user)
    elections_qs = (
        elections_qs
        .annotate(
            votes_cast=Count('votes', distinct=True),
            candidates_count=Count('candidates', distinct=True),
        )
        .order_by('-start_time')
    )

    # Convert to list so we can attach computed fields
    elections_list = list(elections_qs)

    # Compute per-election turnout percent and low-turnout flag
    for e in elections_list:
        # compute eligible from VoterStatus to avoid reverse-name ambiguity
        eligible = VoterStatus.objects.filter(election=e).count()
        e.eligible = eligible
        votes_cast = getattr(e, 'votes_cast', 0) or 0
        e.turnout_pct = round((votes_cast / eligible * 100), 2) if eligible > 0 else 0
        e.low_turnout = (eligible > 0 and (votes_cast / eligible) < 0.3 and e.status == 'active')

    # KPI counts
    total_elections = len(elections_list)
    counts_by_status = {
        'pending': len([1 for e in elections_list if e.status == 'pending']),
        'active': len([1 for e in elections_list if e.status == 'active']),
        'concluded': len([1 for e in elections_list if e.status == 'concluded']),
    }

    # Users/Voters metrics
    voters_total = Profile.objects.filter(role='voter').count()
    voters_confirmed = Profile.objects.filter(role='voter', is_confirmed=True).count()
    approvals_pending = Profile.objects.filter(role='voter', is_confirmed=True, is_approved=False).count()

    # Votes today
    votes_today = Vote.objects.filter(timestamp__date=timezone.now().date()).count()

    # Average turnout across elections with eligible > 0
    turnouts = []
    for e in elections_list:
        eligible = getattr(e, 'eligible', 0) or 0
        votes_cast = getattr(e, 'votes_cast', 0) or 0
        if eligible > 0:
            turnouts.append(votes_cast / eligible)
    avg_turnout_pct = round((sum(turnouts) / len(turnouts) * 100), 2) if turnouts else 0

    # Ending soon (next 48h)
    now = timezone.now()
    # ending soon from the list
    ending_soon = [e for e in elections_list if e.status == 'active' and e.end_time <= now + timedelta(hours=48)]
    ending_soon = sorted(ending_soon, key=lambda x: x.end_time)[:6]

    # Votes per hour (last 24h)
    start = now - timedelta(hours=23)
    vp = (
        Vote.objects.filter(timestamp__gte=start)
        .annotate(h=TruncHour('timestamp'))
        .values('h')
        .annotate(n=Count('id'))
        .order_by('h')
    )
    # Build 24 hourly buckets
    hourly_labels = []
    hourly_counts = []
    bucket = {row['h']: row['n'] for row in vp}
    for i in range(24):
        t = (start + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
        hourly_labels.append(t.strftime('%H:%M'))
        hourly_counts.append(bucket.get(t, 0))

    import json
    chart_labels_json = json.dumps(hourly_labels)
    chart_values_json = json.dumps(hourly_counts)

    # Recent feedback for superusers only
    recent_feedback = []
    if getattr(request.user, 'is_superuser', False):
        recent_feedback = list(Feedback.objects.order_by('-created_at')[:5])

    context = {
    'elections': elections_list,
        'total_elections': total_elections,
        'counts_by_status': counts_by_status,
        'voters_total': voters_total,
        'voters_confirmed': voters_confirmed,
        'approvals_pending': approvals_pending,
        'votes_today': votes_today,
        'avg_turnout_pct': avg_turnout_pct,
        'ending_soon': ending_soon,
        'activity_labels_json': chart_labels_json,
        'activity_values_json': chart_values_json,
        'recent_feedback': recent_feedback,
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
def admin_election_list(request, status: str):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    _sync_election_statuses()
    status = (status or '').lower()
    if status not in {'pending', 'active', 'concluded'}:
        status = 'active'

    base_qs = Election.objects.filter(status=status)
    if getattr(request.user, 'is_superuser', False):
        qs = base_qs
    else:
        qs = base_qs.filter(created_by=request.user)
    qs = (
        qs
        .annotate(
            votes_cast=Count('votes', distinct=True),
            candidates_count=Count('candidates', distinct=True),
        )
        .order_by('-start_time')
    )
    elections = list(qs)
    for e in elections:
        e.eligible = VoterStatus.objects.filter(election=e).count()
        vc = getattr(e, 'votes_cast', 0) or 0
        eg = e.eligible or 0
        e.turnout_pct = round((vc / eg * 100), 2) if eg > 0 else 0

    status_title = status.capitalize()
    return render(request, 'admin_election_list.html', {
        'status': status,
        'status_title': status_title,
        'elections': elections,
    })


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
            # generate a random publish key for the admin to store
            import secrets, hashlib
            publish_key_plain = secrets.token_urlsafe(16)
            publish_key_hash = hashlib.sha256(publish_key_plain.encode('utf-8')).hexdigest()

            eobj = Election.objects.create(
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                start_time=s,
                end_time=e,
                created_by=request.user,
                publish_key_hash=publish_key_hash,
            )
            messages.warning(request, f"Store this publish key safely: {publish_key_plain}")
            messages.info(request, 'You will need this key to publish the results.')
            return redirect('admin_election_list', status='pending')
    else:
        form = ElectionForm()
    return render(request, 'create_election.html', {'form': form})


@login_required
def edit_election(request, election_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    # keep statuses in sync for consistency
    _sync_election_statuses()
    if not _is_super_or_owner(request.user, election):
        return HttpResponseForbidden('Not allowed to edit this election')
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
    if not _is_super_or_owner(request.user, election):
        return HttpResponseForbidden('Not allowed to delete this election')
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
    if not _is_super_or_owner(request.user, election):
        return HttpResponseForbidden('Not allowed to publish this election')
    is_super = getattr(request.user, 'is_superuser', False)
    now = timezone.now()
    is_after_end = now >= election.end_time
    # Key is required only for early publish (before end time) and only for non-superusers
    require_key = (not is_after_end) and bool(election.publish_key_hash) and not is_super

    # GET -> show confirmation (never publish on GET)
    if request.method != 'POST':
        return render(request, 'confirm_delete.html', {
            'object': election,
            'type': 'publish',
            'require_key': require_key,
            'bypass': (is_super or is_after_end),
        })

    # POST -> verify (if required) then publish
    if not (is_super or is_after_end):
        # Block if rate limited
        if election.publish_blocked_until and timezone.now() < election.publish_blocked_until:
            messages.error(request, 'Too many failed attempts. Try again later.')
            return render(request, 'confirm_delete.html', {'object': election, 'type': 'publish', 'require_key': require_key, 'bypass': False})
        key = (request.POST.get('key') or '').strip()
        # If we already have a key hash, verify it
        if bool(election.publish_key_hash):
            if not key:
                messages.error(request, 'Publish key is required')
                return render(request, 'confirm_delete.html', {'object': election, 'type': 'publish', 'require_key': True, 'bypass': False})
            import hashlib
            key_hash = hashlib.sha256(key.encode('utf-8')).hexdigest()
            if key_hash != election.publish_key_hash:
                election.publish_attempts = (election.publish_attempts or 0) + 1
                if election.publish_attempts >= 5:
                    election.publish_blocked_until = timezone.now() + timedelta(minutes=10)
                    election.publish_attempts = 0
                election.save(update_fields=['publish_attempts', 'publish_blocked_until'])
                messages.error(request, 'Invalid publish key')
                return render(request, 'confirm_delete.html', {'object': election, 'type': 'publish', 'require_key': True, 'bypass': False})
        else:
            # First-time publish with no key set: allow setting one
            key_confirm = (request.POST.get('key_confirm') or '').strip()
            if not key or not key_confirm:
                messages.error(request, 'Please provide and confirm a publish key')
                return render(request, 'confirm_delete.html', {'object': election, 'type': 'publish', 'require_key': False, 'bypass': False})
            if key != key_confirm:
                messages.error(request, 'Keys do not match')
                return render(request, 'confirm_delete.html', {'object': election, 'type': 'publish', 'require_key': False, 'bypass': False})
            import hashlib
            election.publish_key_hash = hashlib.sha256(key.encode('utf-8')).hexdigest()

    # Passed verification or bypass; publish results
    election.status = 'concluded'
    election.published_at = now
    election.published_by = request.user
    election.publish_attempts = 0
    election.publish_blocked_until = None
    election.save()
    messages.success(request, 'Results published successfully')
    return redirect('admin_dashboard')


@login_required
def rotate_publish_key(request, election_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    if not _is_super_or_owner(request.user, election):
        return HttpResponseForbidden('Not allowed to rotate key for this election')
    if request.method == 'POST':
        form = PublishKeyRotateForm(request.POST)
        if form.is_valid():
            import hashlib
            # verify current key
            cur = form.cleaned_data['current_key']
            cur_hash = hashlib.sha256(cur.encode('utf-8')).hexdigest()
            if election.publish_key_hash and cur_hash != election.publish_key_hash:
                messages.error(request, 'Current key is incorrect')
            else:
                new_hash = hashlib.sha256(form.cleaned_data['new_key'].encode('utf-8')).hexdigest()
                election.publish_key_hash = new_hash
                election.publish_attempts = 0
                election.publish_blocked_until = None
                election.save(update_fields=['publish_key_hash', 'publish_attempts', 'publish_blocked_until'])
                messages.success(request, 'Publish key updated')
                return redirect('admin_election_list', status=election.status)
    else:
        form = PublishKeyRotateForm()
    return render(request, 'rotate_publish_key.html', {'form': form, 'election': election})


@login_required
def upload_voters(request, election_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden('Admins only')
    election = get_object_or_404(Election, pk=election_id)
    if not _is_super_or_owner(request.user, election):
        return HttpResponseForbidden('Not allowed to manage voters for this election')
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
    if not _is_super_or_owner(request.user, election):
        return HttpResponseForbidden('Not allowed to manage candidates for this election')
    if request.method == 'POST':
        form = CandidateForm(request.POST, request.FILES)
        if form.is_valid():
            Candidate.objects.create(
                election=election,
                name=form.cleaned_data['name'],
                bio=form.cleaned_data['bio'],
                photo=form.cleaned_data.get('photo') or None,
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
    if not _is_super_or_owner(request.user, election):
        return HttpResponseForbidden('Not allowed to view candidates for this election')
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
    if not _is_super_or_owner(request.user, candidate.election):
        messages.error(request, 'Not allowed to edit this candidate')
        return redirect('admin_dashboard')
    if request.method == 'POST':
        form = CandidateForm(request.POST, request.FILES)
        if form.is_valid():
            candidate.name = form.cleaned_data['name']
            candidate.bio = form.cleaned_data['bio']
            # update photo only if a new file is provided
            new_photo = form.cleaned_data.get('photo')
            if new_photo:
                candidate.photo = new_photo
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
    if not _is_super_or_owner(request.user, candidate.election):
        messages.error(request, 'Not allowed to delete this candidate')
        return redirect('admin_dashboard')
    if request.method == 'POST':
        candidate.delete()
        return redirect('list_candidates', election_id=election_id)
    return render(request, 'confirm_delete.html', {'object': candidate, 'type': 'candidate'})


# Internal: keep Election.status aligned with time windows
def _sync_election_statuses():
    now = timezone.now()
    # Move pending -> active when start time reached
    Election.objects.filter(status='pending', start_time__lte=now).update(status='active')
    # If an active election was edited to a future start, revert to pending
    Election.objects.filter(status='active', start_time__gt=now).update(status='pending')
    # Auto-conclude when end time reached (publish automatically)
    Election.objects.filter(end_time__lte=now).exclude(status='concluded').update(
        status='concluded',
        published_at=now,
        published_by=None,
        publish_attempts=0,
        publish_blocked_until=None,
    )
