#!/usr/bin/env python3
"""Fabrique le paquet Windows de Badgeo (Python portable + bibliothèques Windows + application + interface).

Fonctionne sous Windows, Linux ou macOS : les bibliothèques sont téléchargées pour win_amd64.

    python windows/construire.py --mode essai          # zip de test : clé d'essai 30 jours + outils éditeur de test
    python windows/construire.py --mode production     # dossier prêt pour Inno Setup (clé publique réelle exigée)

Résultat : windows/construction/Badgeo/ ; en mode essai, aussi windows/Badgeo-Test-Windows.zip
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from datetime import date, timedelta
from pathlib import Path

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
BACKEND = PROJET / "backend"
FRONTEND = PROJET / "frontend"
CACHE = ICI / "cache"
SORTIE = ICI / "construction"
PBS = "https://github.com/astral-sh/python-build-standalone/releases/download/20250317/cpython-3.12.9+20250317-x86_64-pc-windows-msvc-install_only.tar.gz"
WINSW = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"


def etape(t):
    print(f"\n=== {t} ===", flush=True)


def telecharger(url, nom):
    CACHE.mkdir(exist_ok=True)
    f = CACHE / nom
    if f.exists():
        return f
    print(f"  téléchargement {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "badgeo-build"})
    with urllib.request.urlopen(req, timeout=300) as r, open(f.with_suffix(f.suffix + ".part"), "wb") as out:
        shutil.copyfileobj(r, out)
    f.with_suffix(f.suffix + ".part").replace(f)
    return f


def executer(*cmd, **kw):
    print("  $", " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def copier_app(dest):
    dest.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "tests.py")
    for d in ("config", "apps"):
        shutil.copytree(BACKEND / d, dest / d, ignore=ignore)
    shutil.copy2(BACKEND / "manage.py", dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["essai", "production"], default="essai")
    ap.add_argument("--jours", type=int, default=30, help="durée de la clé d'essai")
    a = ap.parse_args()
    stage = SORTIE / "Badgeo"
    shutil.rmtree(SORTIE, ignore_errors=True)
    stage.mkdir(parents=True)

    etape("Interface web")
    dist = FRONTEND / "dist"
    if not (dist / "index.html").exists():
        npm = shutil.which("npm")
        if not npm:
            sys.exit("frontend/dist absent et npm introuvable : lancez « npm ci && npm run build » dans frontend/.")
        executer(npm, "ci", cwd=FRONTEND)
        executer(npm, "run", "build", cwd=FRONTEND)

    etape("Python portable 3.12 pour Windows")
    archive = telecharger(PBS, "python-windows.tar.gz")
    with tarfile.open(archive) as t:
        t.extractall(stage)  # contient « python/ »
    site = stage / "python" / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)

    etape("Bibliothèques (win_amd64, roues binaires uniquement)")
    executer(sys.executable, "-m", "pip", "install", "-q", "-r", ICI / "requirements-windows.txt", "--target", site,
             "--only-binary=:all:", "--platform", "win_amd64", "--python-version", "3.12", "--implementation", "cp")
    # pyzk (protocole ZKTeco) n'existe qu'en source ; il est en Python pur : on en copie le paquet « zk »
    import re
    meta = json.load(urllib.request.urlopen("https://pypi.org/pypi/pyzk/json", timeout=60))
    sdist = next(u for u in meta["urls"] if u["packagetype"] == "sdist")
    tgz = telecharger(sdist["url"], "pyzk.tar.gz")
    with tarfile.open(tgz) as t:
        membres = [m for m in t.getmembers() if re.search(r"/zk/[^/]+\.py$", m.name)]
        if not membres:
            sys.exit("Paquet zk introuvable dans pyzk.")
        for m in membres:
            m.name = "zk/" + m.name.rsplit("/", 1)[1]
            t.extract(m, site)

    etape("Application")
    app = stage / "app"
    copier_app(app)
    shutil.copytree(dist, app / "frontend_dist")
    shutil.copy2(ICI / "lanceur.py", stage)
    for f in ("badgeo-service.xml",):
        shutil.copy2(ICI / f, stage)
    cle_fichier = app / "apps" / "licensing" / "cle_publique.py"

    if a.mode == "essai":
        etape("Clés d'essai (paire dédiée : sans rapport avec les clés de production)")
        sys.path.insert(0, str(BACKEND))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django
        django.setup()
        from apps.licensing.licence import generer_paire_de_cles, signer, MODULES
        from django.utils import timezone
        privee, publique = generer_paire_de_cles()
        cle_fichier.write_text(f'"""Clé publique de la version de TEST."""\n\nCLE_PUBLIQUE = "{publique}"\n', encoding="utf-8")
        fin = timezone.localdate() + timedelta(days=a.jours)
        cle = signer("*", "Version de test", list(MODULES), 25, 5, fin, cle_privee=privee)
        (stage / "CLE_ESSAI.txt").write_text(cle + "\n", encoding="utf-8")
        ed = stage / "editeur-test"
        ed.mkdir()
        (ed / "cle_privee_TEST.txt").write_text(privee + "\n", encoding="utf-8")
        (ed / "Emettre-licence-test.bat").write_text(
            '@echo off\r\nchcp 65001 >nul\r\nset /p CODE=Code d installation du poste (BDG-XXXX-XXXX-XXXX) ou * pour un essai: \r\n'
            'set /p CLIENT=Nom du client: \r\nset /p JOURS=Duree en jours (ex 30): \r\n'
            'set /p EMP=Plafond employes actifs (vide = illimite): \r\nset /p POINT=Plafond pointeuses (vide = illimite): \r\n'
            'set /p MODS=Modules (mobile,reports,leaves): \r\n'
            'set /p P=<"%~dp0cle_privee_TEST.txt"\r\nset BADGEO_LICENCE_CLE_PRIVEE=%P%\r\n'
            'set ARGS=%CODE% --client "%CLIENT%" --jours %JOURS%\r\nif not "%EMP%"=="" set ARGS=%ARGS% --employes %EMP%\r\n'
            'if not "%POINT%"=="" set ARGS=%ARGS% --pointeuses %POINT%\r\nif not "%MODS%"=="" set ARGS=%ARGS% --modules %MODS%\r\n'
            'echo.\r\n"%~dp0..\\python\\python.exe" "%~dp0..\\lanceur.py" commande emettre_licence %ARGS%\r\necho.\r\npause\r\n', encoding="utf-8")
        (ed / "LISEZMOI.txt").write_text("Outils de l'éditeur POUR LA VERSION DE TEST uniquement.\r\n"
            "cle_privee_TEST.txt ne signe que les clés de ce paquet de test ; elle est sans rapport avec la clé de production.\r\n", encoding="utf-8")
        bats = {
            "Demarrer-Badgeo.bat": '@echo off\r\nchcp 65001 >nul\r\ntitle Badgeo (laissez cette fenetre ouverte)\r\nset PYTHONUTF8=1\r\n'
                'start "" /min cmd /c "timeout /t 8 >nul & start http://localhost:8000/"\r\n"%~dp0python\\python.exe" "%~dp0lanceur.py"\r\npause\r\n',
            "Charger-donnees-demo.bat": '@echo off\r\nchcp 65001 >nul\r\nset PYTHONUTF8=1\r\n"%~dp0python\\python.exe" "%~dp0lanceur.py" commande migrate --noinput\r\n'
                '"%~dp0python\\python.exe" "%~dp0lanceur.py" commande seed_demo\r\npause\r\n',
            "Code-installation.bat": '@echo off\r\nchcp 65001 >nul\r\nset PYTHONUTF8=1\r\n"%~dp0python\\python.exe" "%~dp0lanceur.py" commande shell -c "from apps.licensing.licence import code_installation as c; print(c())"\r\npause\r\n',
            "Sauvegarde-maintenant.bat": '@echo off\r\nchcp 65001 >nul\r\nset PYTHONUTF8=1\r\n"%~dp0python\\python.exe" "%~dp0lanceur.py" commande shell -c "from apps.backups.services import creer; print(creer(\'manual\', \'console\'))"\r\npause\r\n',
        }
        for nom, contenu in bats.items():
            (stage / nom).write_text(contenu, encoding="utf-8")
        (stage / "LISEZMOI-TEST.txt").write_text(LISEZMOI_TEST.format(jours=a.jours, fin=fin.strftime("%d/%m/%Y")), encoding="utf-8")
    else:
        if 'CLE_PUBLIQUE = ""' in cle_fichier.read_text(encoding="utf-8"):
            sys.exit("Clé publique de licence absente : lancez d'abord « python manage.py generer_cles_licence » (voir windows/LISEZMOI.md).")
        etape("Service Windows (WinSW)")
        shutil.copy2(telecharger(WINSW, "WinSW-x64.exe"), stage / "badgeo-service.exe")

    etape("Fichiers statiques de l'administration")
    env = {**os.environ, "BADGEO_DONNEES": str(SORTIE / "donnees-construction"), "DJANGO_SETTINGS_MODULE": "config.settings_local"}
    executer(sys.executable, "manage.py", "collectstatic", "--noinput", "-v", "0", cwd=app, env=env)
    shutil.rmtree(SORTIE / "donnees-construction", ignore_errors=True)
    for p in app.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)

    if a.mode == "essai":
        etape("Archive zip")
        zip_path = ICI / "Badgeo-Test-Windows.zip"
        zip_path.unlink(missing_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for f in sorted(stage.rglob("*")):
                if f.is_file():
                    z.write(f, Path("Badgeo") / f.relative_to(stage))
        print(f"\nTerminé : {zip_path} ({zip_path.stat().st_size / 1e6:.0f} Mo)")
    else:
        print(f"\nPaquet prêt : {stage} (Inno Setup : voir windows/LISEZMOI.md)")


LISEZMOI_TEST = """BADGEO — VERSION DE TEST POUR WINDOWS
=====================================

Cette version est un essai : aucune installation, rien n'est modifié dans Windows. Elle n'a PAS été testée
avec une vraie pointeuse ZKTeco/UNIS (voir « Ce qui n'est pas validé » plus bas).

1. Décompressez ce dossier (clic droit > Extraire tout) dans un chemin simple, ex. C:\\Badgeo-Test
2. Double-cliquez sur  Demarrer-Badgeo.bat  (laissez la fenêtre noire ouverte : c'est le serveur).
   Si Windows demande l'autorisation du pare-feu : « Réseaux privés » suffit pour un test sur ce PC.
3. Le navigateur s'ouvre sur http://localhost:8000
4. ACTIVATION : copiez le contenu de CLE_ESSAI.txt dans l'écran d'activation (valable jusqu'au {fin}, 25 employés,
   5 pointeuses, tous modules). Pour tester une licence liée à ce poste : Code-installation.bat, puis
   editeur-test\\Emettre-licence-test.bat.
5. CONNEXION : utilisateur admin ; le mot de passe est dans  C:\\ProgramData\\Badgeo\\identifiants-initiaux.txt
   (créé au premier démarrage, à changer immédiatement).
6. Pour voir l'application remplie : arrêtez le serveur (fermer la fenêtre), lancez Charger-donnees-demo.bat
   (données FICTIVES, comptes demo_admin / demo_rh / demo_sophie, mot de passe Demo-Badgeo-2026!), puis Demarrer-Badgeo.bat.
   Les pointages « [SIMULATION] » ne prouvent rien sur les vraies pointeuses.

SAUVEGARDES : menu « Sauvegardes » (administrateur). Dossier : C:\\ProgramData\\Badgeo\\sauvegardes
DONNEES      : C:\\ProgramData\\Badgeo (base badgeo.sqlite3, journaux). Supprimer ce dossier = repartir de zéro.
LICENCE      : expirée = lecture seule (la sauvegarde reste possible).
PORT         : variable BADGEO_PORT (8000 par défaut).

Ce qui n'est pas validé : la communication avec de vraies pointeuses ; l'adaptateur UNIS n'est qu'un squelette.
Journaux : C:\\ProgramData\\Badgeo\\journaux\\badgeo.log
"""

if __name__ == "__main__":
    main()
