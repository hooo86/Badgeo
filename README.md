# Badgeo – gestion des pointeuses ZKTeco / UNIS

Phase 1 (backend) : modèle de données, module appareils, synchronisation sans perte.

## Démarrage
```bash
cp .env.example .env && docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```
API : `/api/devices/`, `/api/devices/{id}/test_connection/`, `/api/devices/{id}/sync/`, `/api/sync-logs/`, `/api/employees/`, `/api/punches/`.

## Fonctionnalités (voir `docs/ANALYSE_ET_PLAN.md` pour l'état détaillé)
- Pointeuses ZKTeco (protocole ZK, **non testé sur appareil réel**), synchronisation idempotente avec reprise ; UNIS : squelette.
- Personnel, structures, import/export CSV/Excel, correspondance identifiants pointeuse ↔ matricule.
- Horaires fixes/variables/nuit/rotations, jours fériés, congés et autorisations.
- Moteur de présence (`docs/REGLES_PRESENCE.md`), anomalies, corrections avec validation à deux personnes.
- Tableau de bord, 11 rapports (JSON/CSV/Excel/PDF), journal d'audit, rôles avec périmètre.
- Interface web responsive et application mobile employé (pointer, historique, planning), inspirées du design Stitch « Application Gestion de Pointeuse ».

- Licences signées liées au poste (modules, plafonds, expiration en lecture seule), sauvegardes chiffrées, planifiées et restaurables, version Windows (zip de test, installateur).

- Interface en **français, anglais et arabe** (écriture de droite à gauche), **mode clair / sombre / automatique**, icônes et polices embarquées (fonctionne hors connexion) ; thème repris des écrans Stitch « Badgeo ». Les fichiers exportés (Excel/CSV/PDF) et la plupart des messages du serveur restent en français.

Documentation : `docs/LICENCES_ET_SAUVEGARDES.md`, `windows/LISEZMOI.md`, `docs/INSTALLATION.md`, `docs/API.md`, `docs/REGLES_PRESENCE.md`. Développement : `cd backend && python manage.py test` ; `python manage.py seed_demo` pour des données simulées.

## Garanties anti-perte
- La mémoire de la pointeuse n'est jamais effacée par l'application.
- Insertion idempotente : contrainte unique (appareil, id utilisateur, horodatage).
- En cas d'échec : état enregistré, nouvelle tentative avec backoff exponentiel (Celery), le cycle planifié reprend ensuite.

## Limites actuelles
- ZKTeco via `pyzk` (TCP/UDP), jamais exécuté sur un appareil réel. L'adaptateur UNIS est un squelette : le protocole dépend du modèle exact. Le mode ADMS (push) n'est pas implémenté.
- Pas de géolocalisation ni de balises (iBeacon/NFC) : le pointage mobile est désactivé par défaut et peut être limité au réseau de l'entreprise.
- Exports de paie (Sage, ADP…) non implémentés ; gestion des utilisateurs et affectations d'horaires via API/admin seulement (pas d'écran).

## Phase 2 – Utilisateurs, rôles, audit (terminée côté API)
- Rôles : `sysadmin`, `device_admin`, `hr_manager`, `hr_staff`, `dept_head`, `viewer`. Les rôles `dept_head` et `viewer` ne voient que leur périmètre (unités organisationnelles et leurs sous-unités) ; sans périmètre ils ne voient rien.
- Un superuser Django est traité comme `sysadmin`. Un utilisateur sans profil n'a aucun accès.
- Droits par défaut : appareils = écriture `sysadmin`/`device_admin`; personnel = écriture RH; utilisateurs = `sysadmin`; journal d'audit = `sysadmin`/`hr_manager`.
- Connexion : `POST /api/auth/token/` limitée à 5 tentatives/minute (cache Django ; en production avec plusieurs workers, configurer un cache partagé Redis), échecs journalisés.
- Audit immuable (`/api/audit-logs/`) : création/modification/suppression, tests et synchronisations d'appareils, connexions. Les secrets sont retirés.
- La clé de communication des appareils est chiffrée (Fernet) : définir `DEVICE_SECRET_KEY` en production. Perdre cette clé rend les secrets illisibles.
- Mots de passe : hachés par Django, 10 caractères minimum. En production (`DJANGO_DEBUG=0`) : cookies sécurisés, HSTS, redirection HTTPS (à placer derrière un reverse proxy TLS).

## Interface : langues, thème, icônes
- Textes : le français sert de clé (`t("Texte")`) ; traductions dans `frontend/src/locales/{en,ar}.ts`. `npm run i18n` vérifie que tout est traduit (exécuté aussi par le workflow Windows).
- Thème : jetons CSS dans `frontend/src/theme.css` (clair et sombre), choix mémorisé par navigateur.
- Icônes : Material Symbols, police réduite aux icônes utilisées (`frontend/scripts/icon_names.txt`, `npm run icons` pour vérifier). Pour en ajouter : ajouter le nom à la liste, régénérer la police avec l'API Google Fonts (`icon_names=`) et remplacer `public/fonts/material-symbols.woff2`.
