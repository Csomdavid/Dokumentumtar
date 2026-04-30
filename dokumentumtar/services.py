import os
import uuid
import shutil
import logging
from cryptography.fernet import Fernet
from django.conf import settings
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader, PdfWriter
import hashlib
import time
from pathlib import Path
import datetime
from .models import Document, AuditLog

# Django saját loggere
logger = logging.getLogger(__name__)

# --- Könyvtárszerkezet és Kriptográfia beállítása ---
# A BASE_DIR a core/settings.py-ból jön, így mindig pontos az abszolút útvonal
STORAGE_DIR = settings.BASE_DIR / "storage"
KEY_FILE = STORAGE_DIR / "secret.key"
UPLOADS_DIR = STORAGE_DIR / "uploads"
ARCHIVE_DIR = STORAGE_DIR / "archive"
TEMP_DIR = STORAGE_DIR / "temp"

for d in [STORAGE_DIR, UPLOADS_DIR, ARCHIVE_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

if not KEY_FILE.exists():
    KEY_FILE.write_bytes(Fernet.generate_key())
    logger.info("Új titkosítási kulcs (secret.key) generálva a Django projekthez.")

# Globális Fernet példány
FERNET = Fernet(KEY_FILE.read_bytes())


# --- Kriptográfiai Alapműveletek ---

def encrypt_and_save_file(uploaded_file, output_path: str) -> bool:
    #Egy weben keresztül feltöltött fájl (InMemoryUploadedFile) nyers bájtjainak titkosítása és lemezre mentése.

    try:
        data = uploaded_file.read()
        encrypted = FERNET.encrypt(data)

        with open(output_path, "wb") as f:
            f.write(encrypted)

        return True
    except Exception as e:
        logger.error(f"Encrypt hiba ({output_path}): {e}")
        return False


def decrypt_file(enc_path: str, output_path: str) -> bool:
    #Fájl visszafejtése a lemezen (pl. letöltéshez vagy megtekintéshez).
    try:
        with open(enc_path, "rb") as f:
            encrypted = f.read()

        decrypted = FERNET.decrypt(encrypted)

        with open(output_path, "wb") as f:
            f.write(decrypted)

        return True
    except Exception as e:
        logger.error(f"Decrypt hiba ({enc_path}): {e}")
        return False


def create_temp_decrypted_file(rel_enc_path: str) -> str | None:

    enc_path = settings.BASE_DIR / rel_enc_path

    if not enc_path.exists():
        logger.error(f"Temp visszafejtés sikertelen, hiányzó fájl: {enc_path}")
        return None

    # Egyedi azonosító a fájlnak (ne akadjanak össze a felhasználók a weben!)
    temp_path = TEMP_DIR / f"temp_{uuid.uuid4().hex}.pdf"

    if decrypt_file(str(enc_path), str(temp_path)):
        return str(temp_path)
    return None


def clear_temp_files():
    # Kiüríti a temp mappát.

    try:
        temp_files = TEMP_DIR.glob("temp_*.pdf")
        deleted_count = 0
        for f in temp_files:
            if f.is_file():
                try:
                    f.unlink()
                    deleted_count += 1
                except Exception as error:
                    logger.error(f"Temp fájl törlése sikertelen ({f.name}): {error}")

        if deleted_count > 0:
            logger.info(f"Temp mappa takarítása kész: {deleted_count} fájl törölve.")
    except Exception as e:
        logger.error(f"clear_temp_files hiba: {e}")


def archive_file_physically(rel_filepath: str) -> str | None:
    # Átmozgatja a titkosított fájlt az uploads mappából az archive mappába.

    try:
        source_path = settings.BASE_DIR / rel_filepath

        if not source_path.exists() or "archive" in rel_filepath:
            return None

        filename = source_path.name
        target_path = ARCHIVE_DIR / filename

        shutil.move(str(source_path), str(target_path))

        return f"storage/archive/{filename}"
    except Exception as e:
        logger.error(f"Fájl archiválási hiba: {e}")
        return None


def auto_archive_expired_documents():
    # Megkeresi a lejárt dokumentumokat, és automatikusan az archívumba mozgatja őket.

    today = datetime.date.today()

    expired_docs = Document.objects.filter(
        valid_until__lt=today
    ).exclude(filepath__icontains='archive')

    archived_docs = []
    for doc in expired_docs:
        # ELLENŐRZÉS: Csak akkor próbáljuk mozgatni, ha a fájl tényleg létezik a lemezen
        if os.path.exists(doc.filepath):
            new_path = archive_file_physically(doc.filepath)

            if new_path:
                doc.filepath = new_path
                doc.save()

                # Naplózás a biztonság és visszanézhetőség érdekében
                AuditLog.objects.create(
                    username="SYSTEM",
                    action="AUTO_ARCHIVE",
                    details=f"Automatikus archiválás lejárat miatt: {doc.title}",
                    category="activity"
                )
                archived_docs.append(doc)
        else:
            # Ha az adatbázisban ott van, de a fájlrendszerben nincs, naplózzuk a hibát a konzolra
            print(f"Hiba: A fájl nem található a megadott útvonalon: {doc.filepath}")

    return archived_docs


def create_watermark_layer(text):
    #Létrehoz egy átlátszó PDF réteget a megadott szöveggel.
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    can.setFillGray(0.5, 0.3)
    can.setFont("Helvetica", 40)

    can.saveState()
    can.translate(300, 450)
    can.rotate(45)
    can.drawCentredString(0, 0, text)
    can.restoreState()

    can.save()
    packet.seek(0)
    return packet


def apply_watermark(input_pdf_path, watermark_text):
    # Ráhelyezi a vízjelet az összes oldalra és visszaadja az új fájl útvonalát.
    output_path = str(input_pdf_path).replace(".pdf", "_wm.pdf")

    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    watermark_pdf = PdfReader(create_watermark_layer(watermark_text))
    watermark_page = watermark_pdf.pages[0]

    for page in reader.pages:
        # Összefésüljük az eredeti oldalt a vízjellel
        page.merge_page(watermark_page)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path

def calculate_hash(file_data):
    # SHA-256 hash generálása a fájl tartalmából.
    sha256_hash = hashlib.sha256()
    # Ha a file_data egy fájlobjektum, bájtonként olvassuk
    if hasattr(file_data, 'chunks'):
        for chunk in file_data.chunks():
            sha256_hash.update(chunk)
    else:
        sha256_hash.update(file_data)
    return sha256_hash.hexdigest()


def cleanup_temp_files(threshold_minutes=15):
    """
    Automatikusan törli a megadott időnél régebbi ideiglenes fájlokat.
    Ez megakadályozza a tárhely betelését és javítja a biztonságot.
    """
    now = time.time()
    cutoff = now - (threshold_minutes * 60)

    temp_path = Path(TEMP_DIR)

    if not temp_path.exists():
        return

    deleted_count = 0
    for file in temp_path.glob("temp_*"):
        if file.is_file():
            if os.path.getmtime(file) < cutoff:
                try:
                    file.unlink()
                    deleted_count += 1
                except PermissionError:
                    # Ha a fájl épp nyitva van egy böngészőben, nem tudjuk törölni, békén hagyjuk a következő futásig.
                    pass

    return deleted_count