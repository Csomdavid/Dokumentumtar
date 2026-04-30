from django.urls import path
from . import views

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('upload/', views.document_upload, name='document_upload'),
    path('download/<int:doc_id>/', views.document_download, name='document_download'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
    path('document/<int:doc_id>/', views.document_detail, name='document_detail'),

    # --- ÚJ ARCHÍVUM ÚTVONALAK ---
    path('archive/', views.archive_list, name='archive_list'),
    path('archive/<int:doc_id>/', views.document_archive, name='document_archive'),

    # --- JOGOSULTSÁGOK ÚTVONALAI ---
    path('permissions/', views.permission_manager, name='permission_manager'),
    path('permissions/delete/<int:perm_id>/', views.permission_delete, name='permission_delete'),

    # --- PROFIL ÉS JELSZÓCSERE ---
    path('profile/', views.profile_view, name='profile'),

    path('admin-password-reset/<int:user_id>/', views.admin_password_reset, name='admin_password_reset'),

    path('users/', views.user_list, name='user_list'),

    path('dashboard/', views.security_dashboard, name='security_dashboard'),
]