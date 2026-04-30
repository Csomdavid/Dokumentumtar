import os
import datetime
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseForbidden, Http404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.db.models import Q
from django.db.models import Count

from .models import Document, Permission, Employee, AuditLog
# Beimportáljuk a calculate_hash függvényt is a services-ből
from .services import (
    encrypt_and_save_file,
    create_temp_decrypted_file,
    UPLOADS_DIR,
    archive_file_physically,
    apply_watermark,
    calculate_hash,
    cleanup_temp_files,
    auto_archive_expired_documents
)

@login_required
def document_list(request):
    # 1. Automatikus archiválás futtatása minden betöltéskor
    auto_archive_expired_documents()

    # 2. Értesítés kiszámítása: hány dokumentum járt le a legutóbbi belépés óta?
    new_expired_count = 0
    if request.user.last_expiry_check:
        # Azokat számoljuk, amik a két időpont között jártak le
        new_expired_count = Document.objects.filter(
            valid_until__gte=request.user.last_expiry_check.date(),
            valid_until__lt=datetime.date.today()
        ).count()

    # Frissítjük az időpontot a mostanira
    request.user.last_expiry_check = datetime.datetime.now()
    request.user.save(update_fields=['last_expiry_check'])

    """
    Listázza a dokumentumokat keresési funkcióval.
    Kiberbiztonság: Csak a nem archivált, és jogosultsággal rendelkező fájlok.
    """
    query = request.GET.get('q')  # Keresési paraméter kinyerése

    if request.user.role == 'admin':
        # EXCLUDE: Kivesszük azokat, amiknek az útvonalában benne van az 'archive' szó
        docs = Document.objects.exclude(filepath__icontains='archive')
    else:
        docs = Document.objects.filter(permissions__employee=request.user).exclude(
            filepath__icontains='archive').distinct()

    # Keresési szűrés alkalmazása, ha van megadott kulcsszó
    if query:
        docs = docs.filter(
            Q(title__icontains=query) |
            Q(filename__icontains=query)
        )

    docs = docs.order_by('-created_at')

    docs = [doc for doc in docs if os.path.exists(doc.filepath)]

    context = {
        'docs': docs,
        'query': query,
        'new_expired_count': new_expired_count # Ezt adjuk át a sablonnak
    }
    return render(request, 'dokumentumtar/document_list.html', context)


@login_required
def document_upload(request):
    """
    Kezeli a fájlfeltöltést, meghívja a titkosítót, és regisztrálja az adatbázisban.
    """
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        # Kinyerjük az alapértékeket (ha üres, legyen None)
        valid_from_raw = request.POST.get('valid_from')
        valid_until_raw = request.POST.get('valid_until')
        pdf_file = request.FILES.get('pdf_file')

        # 1. Alapvető validálás
        if not pdf_file or not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, "Csak PDF fájl tölthető fel!")
            return redirect('document_upload')
        
        # 25 MB
        MAX_UPLOAD_SIZE = 25 * 1024 * 1024 
        if pdf_file.size > MAX_UPLOAD_SIZE:
            current_size_mb = pdf_file.size / (1024 * 1024)
            messages.error(request, f"A fájl túl nagy! Maximum 25 MB tölthető fel. (Az Ön fájlja: {current_size_mb:.2f} MB)")
            return redirect('document_upload')

        if not title:
            messages.error(request, "A cím megadása kötelező!")
            return redirect('document_upload')

        # 2. LOGIKAI VALIDÁCIÓ: Dátumok ellenőrzése
        # Csak akkor ellenőrizzük, ha mindkét dátumot megadták
        if valid_from_raw and valid_until_raw:
            try:
                from_date = datetime.datetime.strptime(valid_from_raw, '%Y-%m-%d')
                until_date = datetime.datetime.strptime(valid_until_raw, '%Y-%m-%d')

                if until_date < from_date:
                    messages.error(request, "Logikai hiba: Az érvényesség vége nem lehet korábbi a kezdeténél!")
                    return redirect('document_upload')
            except ValueError:
                messages.error(request, "Érvénytelen dátumformátum!")
                return redirect('document_upload')

        # --- Integritás: SHA-256 Hash számítása ---
        f_hash = calculate_hash(pdf_file)
        pdf_file.seek(0) # Visszatekerés a titkosításhoz!

        # 3. Útvonalak és titkosítás
        orig_name = pdf_file.name
        enc_filename = orig_name.replace(".pdf", ".enc")
        target_path = UPLOADS_DIR / enc_filename

        if encrypt_and_save_file(pdf_file, str(target_path)):
            # 4. Adatbázis bejegyzés (Tisztább mentés)
            doc = Document.objects.create(
                title=title,
                description=description,
                filename=orig_name,
                filepath=f"storage/uploads/{enc_filename}",
                uploader=request.user,
                valid_from=valid_from_raw or None,
                valid_until=valid_until_raw or None,
                file_hash=f_hash
            )

            # 5. Jogosultságok és Audit Log
            Permission.objects.create(document=doc, employee=request.user, permission_type='owner')
            admins = Employee.objects.filter(role='admin').exclude(id=request.user.id)
            for adm in admins:
                Permission.objects.create(document=doc, employee=adm, permission_type='owner')

            AuditLog.objects.create(
                username=request.user.username,
                action="UPLOAD",
                details=f"Új dokumentum (Hash-ellenőrizve): {title}",
                category="activity"
            )

            messages.success(request, f"A '{title}' dokumentum sikeresen feltöltve!")
            return redirect('document_list')
        else:
            messages.error(request, "Hiba történt a titkosítás során!")

    return render(request, 'dokumentumtar/document_upload.html')


@login_required
def document_download(request, doc_id):

    """Biztonságos fájlletöltő és megtekintő végpont dinamikus vízjelezéssel."""
    # --- AUTOMATIKUS TAKARÍTÁS ---
    cleanup_temp_files(threshold_minutes=15)

    doc = get_object_or_404(Document, pk=doc_id)
    # Ellenőrizzük, hogy megtekintés (inline) vagy letöltés (attachment) a kérés
    view_mode = request.GET.get('view') == '1'

    # 1. Jogosultság ellenőrzése (Authorization)
    if request.user.role != 'admin':
        has_perm = Permission.objects.filter(document=doc, employee=request.user).exists()
        if not has_perm:
            # --- Audit Log: Jogosulatlan hozzáférési kísérlet ---
            AuditLog.objects.create(
                username=request.user.username,
                action="UNAUTHORIZED_ACCESS",
                details=f"Jogosulatlan kísérlet ({'Megtekintés' if view_mode else 'Letöltés'}): {doc.title}",
                category="security"
            )
            return HttpResponseForbidden("Kiberbiztonsági riasztás: Nincs jogosultságod a fájlhoz!")

    # 2. Visszafejtés a Service réteggel
    temp_path = create_temp_decrypted_file(doc.filepath)
    if not temp_path:
        raise Http404("A titkosított fájl fizikailag nem található a szerveren.")

    # --- 2/B. INTEGRITÁS-ELLENŐRZÉS: Megnézzük, módosult-e a fájl a tárolás óta ---
    with open(temp_path, 'rb') as f:
        current_hash = calculate_hash(f.read())

    if doc.file_hash and current_hash != doc.file_hash:
        # --- Audit Log: KRITIKUS RIASZTÁS ---
        AuditLog.objects.create(
            username=request.user.username,
            action="INTEGRITY_ALARM",
            details=f"KRITIKUS: A(z) {doc.title} fájl integritása sérült! A hash nem egyezik.",
            category="security"
        )
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return HttpResponseForbidden("Kritikus biztonsági hiba: A fájl tartalma illetéktelenül módosult a szerveren!")

    # 3. DINAMIKUS VÍZJELEZÉS (Csak megtekintés módban)
    final_path = temp_path
    if view_mode:
        # Adatok gyűjtése a vízjelhez a nyomonkövethetőség érdekében
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        watermark_text = f"BIZALMAS - {request.user.username} - {timestamp}"

        # Vízjel ráhelyezése a visszafejtett ideiglenes fájlra
        final_path = apply_watermark(temp_path, watermark_text)

    # --- Audit Log: Művelet specifikus naplózása ---
    action_type = "VIEW" if view_mode else "DOWNLOAD"
    action_text = "megtekintve (vízjelezve)" if view_mode else "letöltve"

    AuditLog.objects.create(
        username=request.user.username,
        action=action_type,
        details=f"Dokumentum visszafejtve (Integritás OK) és {action_text}: {doc.title}",
        category="security"
    )

    # 4. Biztonságos fájlküldés
    # as_attachment=True -> letöltés; as_attachment=False -> böngészőben megnyitás (inline)
    return FileResponse(
        open(final_path, 'rb'),
        as_attachment=not view_mode,
        filename=doc.filename
    )


@login_required
def archive_list(request):
    """
    Kiberbiztonság: Listázza az archivált dokumentumokat keresési funkcióval.
    """
    query = request.GET.get('q')

    if request.user.role == 'admin':
        docs = Document.objects.filter(filepath__icontains='archive')
    else:
        docs = Document.objects.filter(
            filepath__icontains='archive',
            permissions__employee=request.user
        ).distinct()

    if query:
        docs = docs.filter(
            Q(title__icontains=query) |
            Q(filename__icontains=query)
        )

    docs = docs.order_by('-created_at')

    docs = [doc for doc in docs if os.path.exists(doc.filepath)]

    return render(request, 'dokumentumtar/archive_list.html', {'docs': docs, 'query': query})


@login_required
def document_archive(request, doc_id):
    """
    Archiválási művelet. Szigorú Access Control: csak Admin hajthatja végre.
    """
    if request.user.role != 'admin':
        return HttpResponseForbidden("Kiberbiztonsági riasztás: Csak adminisztrátorok archiválhatnak!")

    doc = get_object_or_404(Document, pk=doc_id)

    if 'archive' in doc.filepath:
        messages.warning(request, "Ez a dokumentum már archiválva van.")
        return redirect('document_list')

    # Fizikai mozgatás a Service réteggel
    new_path = archive_file_physically(doc.filepath)

    if new_path:
        doc.filepath = new_path
        doc.save()

        # --- Audit Log: Archiválás naplózása ---
        AuditLog.objects.create(
            username=request.user.username,
            action="ARCHIVE",
            details=f"Dokumentum archiválva: {doc.title}",
            category="activity"
        )

        messages.success(request, f"A '{doc.title}' dokumentum sikeresen archiválva lett!")
    else:
        messages.error(request, "Hiba történt a fájl fizikai archiválása során.")

    return redirect('document_list')


@login_required
def permission_manager(request):
    """
    Jogosultságok kezelése szigorított szabályokkal.
    """
    if request.user.role != 'admin':
        return HttpResponseForbidden("Kiberbiztonsági riasztás!")

    if request.method == 'POST':
        doc_id = request.POST.get('document')
        user_id = request.POST.get('employee')
        permission_type = request.POST.get('permission_type')

        if doc_id and user_id and permission_type:
            doc = get_object_or_404(Document, id=doc_id)
            employee = get_object_or_404(Employee, id=user_id)

            # --- ÚJ BIZTONSÁGI SZABÁLY: Másik admin jogait nem módosíthatod ---
            if employee.role == 'admin' and employee != request.user:
                messages.error(request, f"Biztonsági korlátozás: {employee.username} (Admin) jogosultságait nem módosíthatod!")
                return redirect('permission_manager')

            perm, created = Permission.objects.update_or_create(
                document=doc,
                employee=employee,
                defaults={'permission_type': permission_type}
            )

            AuditLog.objects.create(
                username=request.user.username,
                action="PERMISSION_CHANGE",
                details=f"Jogosultság módosítva: {employee.username} -> {doc.title} ({permission_type})",
                category="security"
            )
            messages.success(request, f"Jogosultság frissítve: {employee.username} -> {doc.title}")

        return redirect('permission_manager')

    # A GET rész marad változatlan...
    permissions = Permission.objects.select_related('document', 'employee').all().order_by('document__title')
    documents = Document.objects.exclude(filepath__icontains='archive').order_by('title')
    employees = Employee.objects.filter(is_active=True).order_by('username')

    context = {
        'permissions': permissions,
        'documents': documents,
        'employees': employees,
    }
    return render(request, 'dokumentumtar/permissions.html', context)


@login_required
def permission_delete(request, perm_id):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Kiberbiztonsági riasztás!")

    perm = get_object_or_404(Permission, id=perm_id)
    target = perm.employee

    # --- HIERARCHIKUS VÉDELEM ---
    # Ha a cél admin, és aki törölni akar az NEM szuperadmin és nem is önmaga
    if target.role == 'admin' and not request.user.is_superuser and target != request.user:
        messages.error(request, "🛡️ Csak a Szuperadmin vonhatja vissza egy másik Admin jogait!")
        return redirect('permission_manager')

    # Saját owner jog védelme (még a szuperadminnak is, nehogy kizárja magát véletlenül)
    if target == request.user and perm.permission_type == 'owner':
        messages.error(request, "Saját adminisztrátori hozzáférésed nem vonhatod vissza!")
    else:
        perm.delete()
        messages.success(request, "Jogosultság visszavonva.")
        AuditLog.objects.create(username=request.user.username, action="PERMISSION_REVOKE", details=f"Jog visszavonva: {target.username}")

    return redirect('permission_manager')


@login_required
def audit_log_view(request):
    """
    Biztonsági naplózás (Audit Log) megjelenítése.
    """
    if request.user.role != 'admin':
        return HttpResponseForbidden("Kiberbiztonsági riasztás: Hozzáférés megtagadva!")

    logs = AuditLog.objects.all().order_by('-timestamp')[:500]
    return render(request, 'dokumentumtar/audit_log.html', {'logs': logs})


@login_required
def profile_view(request):
    """
    Felhasználói profil és biztonságos jelszócsere.
    Kiberbiztonság: A jelszócsere után érvényteleníti a régi munkameneteket,
    de a jelenlegit frissíti (update_session_auth_hash).
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            # Jelszó mentése
            user = form.save()
            # Fontos: Frissíti a session-t, hogy ne dobja ki a felhasználót a csere után
            update_session_auth_hash(request, user)

            # --- Audit Log: Jelszócsere naplózása ---
            AuditLog.objects.create(
                username=request.user.username,
                action="PASSWORD_CHANGE",
                details="Sikeres jelswómódosítás a profil oldalon.",
                category="security"
            )

            messages.success(request, 'A jelszavadat sikeresen frissítettük!')
            return redirect('profile') # <--- Ellenőrizd a nevet a urls.py-ban!
        else:
            # Ha a form nem valid (pl. nem egyeznek a jelszavak)
            messages.error(request, 'Hiba történt. Kérlek, ellenőrizd a megadott adatokat!')
    else:
        form = PasswordChangeForm(request.user)

    # A 'user' objektumot nem kell külön átadni, a Django alapból beteszi a context-be
    return render(request, 'dokumentumtar/profile.html', {'form': form})


@login_required
def admin_password_reset(request, user_id):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Tiltott művelet!")

    target_user = get_object_or_404(Employee, id=user_id)

    # --- KRITIKUS BIZTONSÁGI SZABÁLY ---
    # Szuperadmin jelszava a weben keresztül ÉRINTHETETLEN
    if target_user.is_superuser:
        messages.error(request, "🛡️ Biztonsági korlátozás: A Szuperadmin jelszava nem módosítható a webes felületről!")
        return redirect('user_list')

    # Sima admin nem resetelheti egy másik admin jelszavát (csak a szuperadmin)
    if target_user.role == 'admin' and not request.user.is_superuser:
        messages.error(request, "🛡️ Másik adminisztrátor jelszavát csak a Szuperadmin állíthatja alaphelyzetbe!")
        return redirect('user_list')

    if request.method == 'POST':
        form = SetPasswordForm(target_user, request.POST)
        if form.is_valid():
            form.save()
            AuditLog.objects.create(username=request.user.username, action="ADMIN_PW_RESET", details=f"Jelszó kényszerítve: {target_user.username}")
            messages.success(request, f"Jelszó sikeresen módosítva: {target_user.username}")
            return redirect('permission_manager')
    else:
        form = SetPasswordForm(target_user)

    return render(request, 'dokumentumtar/admin_password_reset.html', {'form': form, 'target_user': target_user})


@login_required
def user_list(request):
    """
    Összes felhasználó listázása az adminisztrátorok számára.
    """
    if request.user.role != 'admin':
        return HttpResponseForbidden("Nincs jogosultságod a felhasználók listázásához!")

    # Minden aktív munkatárs lekérése
    users = Employee.objects.all().order_by('username')

    return render(request, 'dokumentumtar/user_list.html', {'users': users})


@login_required
def security_dashboard(request):
    """
    Kiberbiztonsági vezérlőpult az adminisztrátorok számára.
    Vizualizálja a rendszer eseményeit magyarított címkékkel.
    """
    # 1. Jogosultság ellenőrzése
    if request.user.role != 'admin':
        return HttpResponseForbidden("Csak adminisztrátorok láthatják a biztonsági statisztikákat!")

    # --- AUTOMATIKUS TAKARÍTÁS ÉS NAPLÓZÁS ---
    deleted_count = cleanup_temp_files(threshold_minutes=15)
    if deleted_count and deleted_count > 0:
        AuditLog.objects.create(
            username="SYSTEM",
            action="CLEANUP",
            details=f"Automatikus karbantartás: {deleted_count} db ideiglenes fájl törölve.",
            category="activity"
        )

    # 2. Fordító szótár az adatbázis kódokhoz
    translation_map = {
        'UPLOAD': 'Feltöltés',
        'DOWNLOAD': 'Letöltés',
        'VIEW': 'Megtekintés',
        'ARCHIVE': 'Archiválás',
        'AUTO_ARCHIVE': 'Rendszer archiválás',
        'PERMISSION_CHANGE': 'Jogmódosítás',
        'PASSWORD_CHANGE': 'Jelszócsere',
        'INTEGRITY_ALARM': 'Integritás hiba',
        'UNAUTHORIZED_ACCESS': 'Jogosulatlan kísérlet',
        'ADMIN_PW_RESET': 'Admin jelszóreset',
        'PERMISSION_REVOKE': 'Jog megvonása',
        'UNAUTHORIZED_REVOKE_ATTEMPT': 'Tiltott jogelvonási kísérlet',
        'CLEANUP': 'Rendszertakarítás'
    }

    total_auto_archived = AuditLog.objects.filter(action='AUTO_ARCHIVE').count()

    # 3. Statisztikák lekérése (Nyers adatok)
    sec_events_raw = AuditLog.objects.filter(category='security').values('action').annotate(count=Count('action'))
    act_events_raw = AuditLog.objects.filter(category='activity').values('action').annotate(count=Count('action'))

    # 4. Adatok magyarítása a grafikonhoz (Leképezzük a neveket)
    security_events = [
        {'action': translation_map.get(e['action'], e['action']), 'count': e['count']}
        for e in sec_events_raw
    ]
    activity_events = [
        {'action': translation_map.get(e['action'], e['action']), 'count': e['count']}
        for e in act_events_raw
    ]

    # 5. Kritikus riasztások (Top 5)
    # Itt is érdemes az összes biztonsági szempontból fontos eseményt figyelni
    critical_alerts = AuditLog.objects.filter(
        Q(action='INTEGRITY_ALARM') |
        Q(action='UNAUTHORIZED_ACCESS') |
        Q(action='UNAUTHORIZED_REVOKE_ATTEMPT')
    ).order_by('-timestamp')[:5]

    active_qs = Document.objects.exclude(filepath__icontains='archive')
    archived_qs = Document.objects.filter(filepath__icontains='archive')

    total_active = len([d for d in active_qs if os.path.exists(d.filepath)])
    total_archived = len([d for d in archived_qs if os.path.exists(d.filepath)])

    context = {
        'total_active': total_active,  # A korábbi total_docs helyett (csak aktívak)
        'total_archived': total_archived,  # ÚJ: Összes archivált fájl száma
        'total_users': Employee.objects.count(),
        'total_logs': AuditLog.objects.count(),
        'total_auto_archived': total_auto_archived,  # Ez a korábbi AuditLog alapú szám
        'security_events': security_events,
        'activity_events': activity_events,
        'critical_alerts': critical_alerts,
    }

    return render(request, 'dokumentumtar/dashboard.html', context)


@login_required
def document_detail(request, doc_id):
    """
    Megjeleníti a dokumentum összes metaadatát, beleértve a lejárati dátumokat is.
    """
    doc = get_object_or_404(Document, pk=doc_id)

    # Jogosultság ellenőrzése (hasonlóan a letöltéshez) [cite: 855, 942]
    if request.user.role != 'admin':
        has_perm = Permission.objects.filter(document=doc, employee=request.user).exists()
        if not has_perm:
            return HttpResponseForbidden("Nincs jogosultságod a dokumentum adatainak megtekintéséhez!")

    return render(request, 'dokumentumtar/document_detail.html', {'doc': doc})