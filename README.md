# DOKUMENTUMTÁR
Szakdolgozat 2026

Ez a projekt egy helyi dokumentumtár-rendszer, amely Python alapokon, Django keretrendszer
használatával készült Windows környezetre. A fejlesztés során a kiberbiztonsági és adatbiztonsági szempontok élveztek prioritást.


## 🛠️ Alkalmazott technológiák

- **Keretrendszer:** Django 5.2.12

- **Adatbázis:** SQLite (helyi fájl alapú tárolás)

- **Titkosítás:** Cryptography könyvtár (AES-alapú fájltitkosítás)

- **Audit eszközök:** bandit (statikus biztonsági elemzés), pip-audit (sebezhetőség-vizsgálat)

- **Kódminőség:** black automatikus kódformázó a PEP 8 szabvány betartásához


## 🛡️ Kiberbiztonsági jellemzők
- **Automatizált kulcskezelés:** A rendszer az első telepítéskor kriptográfiailag erős titkosító
kulcsokat generál a secrets modul segítségével, elkerülve a "hard-coded" jelszavak használatát.

- **Környezeti változók:** Érzékeny adatok (pl. Django Secret Key) elkülönített .env fájlban
tárolódnak, amely nem kerül feltöltésre a verziókezelőbe.

- **RBAC (Szerepkör alapú hozzáférés-szabályozás):** Elkülönített adminisztrátori és
felhasználói jogosultsági szintek.

- **Adatvédelem:** Titkosított dokumentumtárolás támogatása (.enc kiterjesztés).


## 📋 Rendszerkövetelmények
- **Operációs rendszer:** Windows 10/11

- **Python:** 3.11 vagy újabb (szükséges a PATH-hoz való hozzáadás)

- **Webböngésző:** Chrome, Firefox vagy Edge (a fejlesztői szerverhez)

- **Webszerver (opcionális):** Apache HTTP Szerver


## 🚀 Telepítés és Inicializálás
A rendszer beállítása teljesen automatizált a TELEPITES.bat fájl segítségével. A script az alábbi lépéseket hajtja végre:  

1. **Virtuális környezet:** Létrehozza a .venv mappát a függőségek izolációjához.  

2. **Biztonsági konfiguráció:** Generál egy egyedi .env fájlt és a fájltitkosításhoz szükséges secret.key állományt.  

3. **Függőségek:** Telepíti a szükséges Python könyvtárakat a requirements.txt alapján.  

4. **Adatbázis:** Elvégzi a migrációkat és az init_db.py futtatásával létrehozza a tesztfelhasználókat.  

5. **Apache integráció:** Elkészíti a helyi útvonalakhoz igazított dokumentumtar.conf konfigurációs fájlt.  

**Futtatás:** Kattintson duplán a TELEPITES.bat fájlra.


## 💻 A program indítása
A sikeres telepítést követően az INDITAS.bat fájllal indítható a rendszer.  

- A script ellenőrzi a környezet meglétét.  

- Automatikusan megnyitja az alapértelmezett böngészőt a [http://127.0.0.1:8000](http://127.0.0.1:8000) címen.  

- Elindítja a Django fejlesztői szervert.


## 👤 Tesztfelhasználók
Az inicializálás során az alábbi fiókok jönnek létre:

- **Szuperfelhasználó:** root_admin (Jelszó: RootPassword456)

- **Adminisztrátor:** admin_tamas (Jelszó: TitkosJelszo123)

- **Felhasználó:** szabo_anna (Jelszó: UserJelszo789)


## 📂 Projektstruktúra leírása
- storage/: Ide kerülnek a feltöltött dokumentumok és a titkosító kulcs.

- deployment/: Az Apache szerverhez szükséges konfigurációs sablonokat tartalmazza.

- .gitignore: Biztosítja, hogy szenzitív adatok (adatbázis, kulcsok, lokális beállítások) ne kerüljenek publikus felületre.
