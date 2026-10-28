# Badgeo pour Windows (édition locale)

Deux livrables, fabriqués par `windows/construire.py` (aussi par le workflow GitHub « Windows »).

| | Version de test | Version de production |
|---|---|---|
| Fichier | `Badgeo-Test-Windows.zip` | `Badgeo-Setup.exe` (Inno Setup + service Windows « Badgeo ») |
| Installation | aucune : décompresser, double-cliquer `Demarrer-Badgeo.bat` | assistant, démarre avec l'ordinateur, raccourci, pare-feu en option |
| Licence | clé d'essai fournie (`CLE_ESSAI.txt`, 30 jours, tous postes) signée par une paire de clés **de test** | clé liée au poste, signée avec **votre** clé privée |
| Données | `C:\ProgramData\Badgeo` | `C:\ProgramData\Badgeo` (jamais effacées, même à la désinstallation) |

Le paquet contient son propre Python 3.12 (python-build-standalone), les bibliothèques Windows et l'interface : rien d'autre à installer. SQLite, serveur Waitress, planificateur intégré (pas de Redis).

## Fabriquer sur GitHub (recommandé)
Onglet **Actions** → **Windows** → **Run workflow** → mode `essai`. Le workflow lance les tests, fabrique le paquet, le **démarre réellement sur Windows** (activation, connexion, changement de mot de passe, sauvegarde) puis publie `Badgeo-Test-Windows` dans les *Artifacts*.

## Fabriquer sur votre machine
    python windows/construire.py --mode essai          # Windows, Linux ou macOS (Python 3.12+, Node 22, Django installé)
    python windows/construire.py --mode production     # puis Inno Setup : ISCC windows\badgeo.iss /DPaquet=windows\construction\Badgeo

## Mise en production (licences)
1. Une seule fois : `cd backend && python manage.py generer_cles_licence`. La clé **publique** est écrite dans `backend/apps/licensing/cle_publique.py` (à committer) ; la clé **privée** s'affiche : gardez-la hors de Git, en lieu sûr. Perdue : plus aucune licence ne peut être émise ; divulguée : n'importe qui peut en fabriquer.
2. Fabriquer `Badgeo-Setup.exe` (mode `production`, ou étiquette `v1.0.0`).
3. Chez le client : installer, ouvrir Badgeo, relever le **code d'installation** (BDG-XXXX-XXXX-XXXX).
4. Chez vous : `BADGEO_LICENCE_CLE_PRIVEE=<clé privée> python manage.py emettre_licence BDG-XXXX-XXXX-XXXX --client "Société" --employes 50 --pointeuses 4 --modules mobile,reports,leaves --jours 365`
5. Le client colle la clé dans l'écran d'activation (sans Internet).

Licence expirée : lecture seule (consultation, rapports, sauvegarde). Installation copiée sur un autre PC : le code change, la clé ne convient plus. Reculer l'horloge ne prolonge pas une licence.

## Support
- Journaux : `C:\ProgramData\Badgeo\journaux\badgeo.log`.
- Redémarrer : Services Windows → Badgeo.
- Port différent de 8000 : variable système `BADGEO_PORT`.
- Sauvegarde chiffrée : variable système `BADGEO_BACKUP_PASSPHRASE` (à conserver séparément).
- Mise à jour : relancer `Badgeo-Setup.exe` ; la base est copiée dans `sauvegardes\avant-mise-a-jour` avant migration (5 dernières).
