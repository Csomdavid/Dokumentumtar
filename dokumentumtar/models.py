import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser


# FELHASZNÁLÓK
class Employee(AbstractUser):

    ROLE_CHOICES = (
        ('user', 'User'),
        ('admin', 'Admin'),
    )

    position = models.CharField(max_length=150, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return f"{self.username} ({self.role})"

    # Új mező a lejárati értesítések követéséhez
    last_expiry_check = models.DateTimeField(null=True, blank=True)


# DOKUMENTUMOK
class Document(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    filename = models.CharField(max_length=255)

    filepath = models.CharField(max_length=500)

    # Külső kulcs a Dolgozóhoz (ON DELETE SET NULL)
    uploader = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')

    valid_from = models.DateField(blank=True, null=True)
    valid_until = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Automatikus timestamp

    file_hash = models.CharField(max_length=64, blank=True, null=True)  # SHA-256 hash helye

    def __str__(self):
        return self.title

    @property
    def expiry_class(self):

        if not self.valid_until:
            return ""

        today = datetime.date.today()
        diff = (self.valid_until - today).days

        if diff <= 7:
            return "table-danger"  # Piros háttér
        elif diff <= 14:
            return "table-warning"  # Sárga háttér
        return ""

# 3. JOGOSULTSÁGOK
class Permission(models.Model):
    TYPE_CHOICES = (
        ('read', 'Read'),
        ('write', 'Write'),
        ('owner', 'Owner'),
    )

    # CASCADE: Ha törlünk egy dokumentumot vagy dolgozót, a jogosultság is tűnjön el (Adatbiztonság)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='permissions')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='permissions')
    permission_type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    # Meta osztály: Egy dokumentumhoz egy dolgozónak csak egyféle jogosultsága lehet (Adatintegritás)
    class Meta:
        unique_together = ('document', 'employee')

    def __str__(self):
        return f"{self.employee.username} -> {self.document.title} ({self.permission_type})"


# AUDIT LOG
class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)

    # Nem kapcsolom ForeignKey-el, hogy ha a felhasználót törlik, a napló akkor is megmaradjon a nevével! (Auditálási alapelv)
    username = models.CharField(max_length=150)
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50, default='activity')

    def __str__(self):
        return f"[{self.timestamp}] {self.username} - {self.action}"