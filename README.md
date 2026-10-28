# Badgeo – gestion des pointeuses ZKTeco / UNIS

Phase 1 (backend) : modèle de données, module appareils, synchronisation sans perte.

## Démarrage
```bash
cp .env.example .env && docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```
API : `/api/devices/`, `/api/devices/{id}/test_connection/`, `/api/devices/{id}/sync/`, `/api/sync-logs/`, `/api/employees/`, `/api/punches/`.

## Garanties anti-perte
- La mémoire de la pointeuse n'est jamais effacée par l'application.
- Insertion idempotente : contrainte unique (appareil, id utilisateur, horodatage).
- En cas d'échec : état enregistré, nouvelle tentative avec backoff exponentiel (Celery), le cycle planifié reprend ensuite.

## Limites actuelles
- ZKTeco via `pyzk` (TCP/UDP). L'adaptateur UNIS est un squelette : le protocole dépend du modèle exact.
- Pas encore : frontend React, horaires/retards, rapports, sauvegarde/restauration.

## Phase 2 – Utilisateurs, rôles, audit (terminée côté API)
- Rôles : `sysadmin`, `device_admin`, `hr_manager`, `hr_staff`, `dept_head`, `viewer`. Les rôles `dept_head` et `viewer` ne voient que leur périmètre (unités organisationnelles et leurs sous-unités) ; sans périmètre ils ne voient rien.
- Un superuser Django est traité comme `sysadmin`. Un utilisateur sans profil n'a aucun accès.
- Droits par défaut : appareils = écriture `sysadmin`/`device_admin`; personnel = écriture RH; utilisateurs = `sysadmin`; journal d'audit = `sysadmin`/`hr_manager`.
- Connexion : `POST /api/auth/token/` limitée à 5 tentatives/minute (cache Django ; en production avec plusieurs workers, configurer un cache partagé Redis), échecs journalisés.
- Audit immuable (`/api/audit-logs/`) : création/modification/suppression, tests et synchronisations d'appareils, connexions. Les secrets sont retirés.
- La clé de communication des appareils est chiffrée (Fernet) : définir `DEVICE_SECRET_KEY` en production. Perdre cette clé rend les secrets illisibles.
- Mots de passe : hachés par Django, 10 caractères minimum. En production (`DJANGO_DEBUG=0`) : cookies sécurisés, HSTS, redirection HTTPS (à placer derrière un reverse proxy TLS).
