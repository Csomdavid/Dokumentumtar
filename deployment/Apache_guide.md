# 📄 DOKUMENTUMTÁR - PRODUKCIÓS TELEPÍTÉSI ÚTMUTATÓ (WINDOWS + APACHE)

Ez az útmutató a rendszer éles (Production) környezetben való üzembe helyezéséhez készült, különös tekintettel az Apache webszerver integrációra és a kiberbiztonsági keményítésre.

💡 **FONTOS MEGJEGYZÉS:** A rendszer úgy lett kialakítva, hogy a **TELEPITES.bat** és **INDITAS.bat** fájlok használatával a telepítési és konfigurációs folyamat nagy része teljesen automatizált. Amennyiben ezeket használja, a manuális beállítások többsége (környezeti változók, adatbázis-inicializálás, konfiguráció generálás) nem igényel külön beavatkozást.

## 1. Előfeltételek

A telepítés megkezdése előtt győződjön meg arról, hogy az alábbi komponensek rendelkezésre állnak a Windows környezetben:  

- **Apache 2.4+ (Win64):** Javasolt az Apache Lounge-ról letölthető verzió.

    Az Apache Lounge letöltési oldala: https://www.apachelounge.com/download/

- **Visual C++ Redistributable:** Az Apache futtatásához szükséges csomag.

    Visual C++ Redistributable letöltése: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170

- **Python környezet:** A **TELEPITES.bat** automatikusan létrehozza a virtuális környezetet és telepíti a függőségeket a requirements_production.txt alapján.


## 2. Apache Konfiguráció (Automatizált folyamat)

Az Apache és a Python (Django) közötti kapcsolatot a mod_wsgi modul biztosítja.

1. **Modul betöltése:** Futtassa a mod_wsgi-express module-config parancsot, majd a kimenetet másolja a httpd.conf fájl elejére.

2. **Automata generálás:** Futtassa le a gyökérkönyvtárban található **TELEPITES.bat** fájlt.

    - Ez automatikusan kitölti a deployment/dokumentumtar.conf állományt a helyi útvonalakkal.  

3. **Aktiválás:**

    - Másolja a generált .conf fájlt az Apache conf/extra/ mappájába.

    - Adja hozzá az Include conf/extra/dokumentumtar.conf sort a fő httpd.conf végéhez.


## 3. Kiberbiztonsági beállítások

Mivel a dolgozat prioritása az adatbiztonság, az alábbi lépések a rendszer részét képezik:

- **Környezet váltás:** A TELEPITES.bat által generált .env fájlban az APP_ENV értékét állítsa 'prod'-ra.

    - Hatása: Kikapcsolja a hibakeresési (DEBUG) módot, aktiválja a SESSION_COOKIE_SECURE védelmet és a HSTS fejléceket.

- **Adatbázis és tároló jogosultságok:** Az Apache szolgáltatást futtató felhasználónak írási jogot kell kapnia a storage/ mappára és a db.sqlite3 fájlra.

💡 **FONTOS:** A telepítő script futtatása során az adatbázis-inicializáló gondoskodik a tesztfelhasználók (admin/user) és az alapértelmezett szerepkörök beállításáról. Így a rendszer az első indítás után azonnal, előre konfigurált és biztonságos hozzáférésekkel használható.

- **Automatizált Biztonsági Audit:** A rendszer tartalmazza a bandit és pip-audit eszközöket, amelyekkel a kód és a függőségek sebezhetősége ellenőrizhető.
  
