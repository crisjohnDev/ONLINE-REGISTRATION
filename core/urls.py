from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('new-registration/', views.new_registration, name='new-registration'),
    path('transfer-record/', views.transfer, name='transfer'),
    path('reactivation-of-record/', views.reactivation, name='reactivation'),
    path('update-information/', views.update_info, name='update'),
    path('reinstatement/', views.reinstatement, name='reinstatement'),
    path('success/<int:resident_id>/', views.success, name='success'),
    path("already-registered/<int:resident_id>/", views.already_registered, name="already_registered"),
    path('admin-login/', views.login_view, name='login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('new-registration-records/', views.new_registration_view, name='registration-view'),
    path("pre-approve/<int:pk>/", views.pre_approve, name="pre_approve"),
    path("capture-thumbmark/<int:pk>/", views.capture_thumbmark, name="capture_thumbmark"),
    path("registration/reject/<int:pk>/", views.reject_registration, name="reject_registration"),
    path('incoming-transfers/', views.transfers, name='transfers'),
    path('reactivation/', views.voter_reactivation, name="voter-reactivation"),
    path('voter-correction/', views.voter_correction, name='voter-correction'),
    path('voter_reinstatement/', views.voter_reinstatement, name='voter-reinstatement'),
    path('audit-logs/', views.audit_logs, name='audit-logs'),
    path('logout/', views.logout_view, name='logout')
]
