from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.voter_dashboard, name='voter_dashboard'),
    path('about/', views.about, name='about'),
    path('vote/<int:election_id>/', views.vote_view, name='vote'),
    path('results/<int:election_id>/', views.results_view, name='results'),
    path('manage-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/create/', views.create_election, name='create_election'),
    path('manage/<int:election_id>/edit/', views.edit_election, name='edit_election'),
    path('manage/<int:election_id>/delete/', views.delete_election, name='delete_election'),
    path('manage/<int:election_id>/upload/', views.upload_voters, name='upload_voters'),
    path('manage/<int:election_id>/publish/', views.publish_results, name='publish_results'),
    path('results/<int:election_id>/export/', views.export_results_csv, name='export_results_csv'),
    path('manage/<int:election_id>/candidates/create/', views.create_candidate, name='create_candidate'),
    path('manage/<int:election_id>/candidates/', views.list_candidates, name='list_candidates'),
    path('manage/<int:election_id>/candidates/<int:candidate_id>/edit/', views.edit_candidate, name='edit_candidate'),
    path('manage/<int:election_id>/candidates/<int:candidate_id>/delete/', views.delete_candidate, name='delete_candidate'),
]
