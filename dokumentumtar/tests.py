import os
from django.test import TestCase
from django.urls import reverse
from datetime import date, timedelta
from .models import Document, Employee, Permission
from .services import auto_archive_expired_documents


class DocumentSecurityTest(TestCase):
    def setUp(self):
        """
        Tesztkörnyezet előkészítése: admin és sima felhasználó létrehozása.
        """
        self.admin_user = Employee.objects.create_user(
            username='testadmin',
            password='password123',
            role='admin'
        )
        self.regular_user = Employee.objects.create_user(
            username='testuser',
            password='password123',
            role='user'
        )
        self.doc = Document.objects.create(
            title="Titkos dokumentum",
            valid_until=date.today() + timedelta(days=30),
            uploader=self.admin_user,
            filepath="storage/uploads/secret.pdf"
        )

    def test_permission_enforcement(self):
        """
        Ellenőrzi, hogy jogosultság nélkül a 'user' nem látja a részleteket,
        de jogosultság megadása után már igen.
        """
        # 1. Bejelentkezés sima felhasználóként
        self.client.login(username='testuser', password='password123')

        # 2. Megpróbáljuk elérni a dokumentum részleteit (Info gomb útvonala)
        url = reverse('document_detail', args=[self.doc.id])
        response = self.client.get(url)

        # Jogosultság nélkül 403 Forbidden választ kell kapnunk
        self.assertEqual(response.status_code, 403)

        # 3. Jogosultság hozzáadása az adatbázisban
        Permission.objects.create(
            document=self.doc,
            employee=self.regular_user,
            permission_type='read'
        )

        # 4. Újra megpróbáljuk elérni az oldalt
        response = self.client.get(url)

        # Most már 200 OK választ kell kapnunk
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Titkos dokumentum")

    def test_expiry_logic_colors(self):
        # ... (a korábbi színkódos teszt változatlan marad) ...
        doc_red = Document.objects.create(
            title="Közeli lejárat",
            valid_until=date.today() + timedelta(days=5),
            uploader=self.admin_user
        )
        self.assertEqual(doc_red.expiry_class, "table-danger")

    # tests.py részlet
    import os

    def test_auto_archive_logic(self):
        # Létrehozunk egy valódi tesztfájlt
        test_path = "storage/uploads/test_file.pdf"
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        with open(test_path, "w") as f:
            f.write("test content")

        expired_doc = Document.objects.create(
            title="Már lejárt fájl",
            valid_until=date.today() - timedelta(days=1),
            filepath=test_path,
            uploader=self.admin_user
        )

        auto_archive_expired_documents()
        expired_doc.refresh_from_db()

        # Ellenőrizzük, hogy az útvonal frissült-e
        self.assertIn("archive", expired_doc.filepath)

        # Takarítás: töröljük a tesztfájlt az archívumból
        if os.path.exists(expired_doc.filepath):
            os.remove(expired_doc.filepath)