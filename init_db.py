import os
import secrets
from pathlib import Path
import django

# 1. Kiberbiztonsági inicializálás: Titkosító kulcs automatikus generálása
def setup_security():
    print("\n--- Biztonsagi beallitasok inicializalasa ---")
    
    # Útvonal meghatározása a storage mappához (platformfüggetlen megoldás)
    storage_path = Path(__file__).resolve().parent / "storage"
    key_file = storage_path / "secret.key"

    # Csak akkor generálunk, ha még nem létezik a kulcs
    if not key_file.exists():
        print("[!] Dokumentum-titkosito kulcs nem talalhato. Generalas...")
        
        # 32 bájtos, kriptográfiailag erős kulcs generálása (Base64 formátum)
        new_key = secrets.token_urlsafe(32)
        
        # Mappa létrehozása, ha esetleg hiányozna
        storage_path.mkdir(exist_ok=True)
        
        with open(key_file, "w", encoding="utf-8") as f:
            f.write(new_key)
        print(f"[+] Uj kulcs sikeresen mentve: {key_file}")
    else:
        print("[✓] Dokumentum-titkosito kulcs mar letezik.")

# Futtatjuk a biztonsági setupot, MÉG MIELŐTT a Django betöltődne
setup_security()

# 2. Django környezet inicializálása
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Ezt csak a django.setup() UTÁN lehet importálni
from django.contrib.auth import get_user_model

def initialize_database():
    User = get_user_model()
    
    # 3. Teszt felhasználók adatai: 
    # (username, email, jelszó, is_staff, is_superuser, role)
    users_data = [
        ('root_admin', 'admin@example.com', 'RootPassword456', True, True, 'admin'),
        ('admin_tamas', 'tamas@example.com', 'TitkosJelszo123', True, False, 'admin'),
        ('szabo_anna', 'anna@example.com', 'UserJelszo789', False, False, 'user'),
    ]

    print("\n--- Adatbazis inicializalasa (RBAC setup) ---")

    for username, email, password, is_staff, is_super, role_name in users_data:
        # Ellenőrizzük, létezik-e már a felhasználó
        user = User.objects.filter(username=username).first()
        
        if not user:
            # Felhasználó létrehozása
            if is_super:
                user = User.objects.create_superuser(
                    username=username, 
                    email=email, 
                    password=password
                )
            else:
                user = User.objects.create_user(
                    username=username, 
                    email=email, 
                    password=password,
                    is_staff=is_staff
                )
            print(f"[+] {username} fiok letrehozva.")
        else:
            print(f"[-] {username} mar letezik, csak a jogosultsagokat frissitjuk.")

        # 4. Kiberbiztonsági szempont: A 'role' mező és a jogosultságok kényszerítése
        # Ez biztosítja, hogy a base.html-ben a menük helyesen jelenjenek meg.
        user.role = role_name
        user.is_staff = is_staff
        user.is_superuser = is_super
        user.save() # Ez a sor menti el ténylegesen az adatbázisba!

    print("--- KESZ: Minden felhasznalo beallitva! ---\n")

if __name__ == "__main__":
    initialize_database()