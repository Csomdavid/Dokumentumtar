from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employee, Document, Permission, AuditLog


# Dolgozó modell beállítása
@admin.register(Employee)
class EmployeeAdmin(UserAdmin):

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'position', 'is_staff')

    fieldsets = UserAdmin.fieldsets + (
        ('Extra adatok (Szakdolgozat)', {'fields': ('role', 'position')}),
    )


# Dokumentumok beállítása
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'filename', 'uploader', 'valid_until', 'created_at')
    search_fields = ('title', 'filename')  # Keresőmező bekapcsolása
    list_filter = ('created_at',)  # Oldalsó szűrő bekapcsolása


# Jogosultságok beállítása
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('employee', 'document', 'permission_type')
    list_filter = ('permission_type',)


# Audit Log beállítása
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'username', 'action', 'category')
    list_filter = ('category',)
    search_fields = ('username', 'action')

    # Kibervédelem: Az Audit Logot senki ne tudja módosítani az adminból sem!
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False