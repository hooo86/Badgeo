# Installation, mise à jour, maintenance

## Installation (Ubuntu / VPS / réseau local)
```bash
sudo apt install docker.io docker-compose-v2 git
git clone https://github.com/hooo86/Badgeo.git && cd Badgeo
cp .env.example .env     # renseigner DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DEVICE_SECRET_KEY, BACKUP_PASSPHRASE
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```
Application : `http://serveur:8080`. En production, placer un reverse proxy TLS (Caddy, nginx, Traefik) devant le service `frontend` avec l'en-tête `X-Forwarded-Proto: https`.

Le serveur doit joindre chaque pointeuse en TCP (port 4370 pour le protocole ZK) ; vérifier le routage/VLAN et réserver une IP fixe par appareil.

## Premiers pas
1. Créer les unités organisationnelles (`/admin/` ou API), les horaires, les affectations.
2. Ajouter les pointeuses, cliquer sur « Tester » (un test réussi sur l'appareil réel est la seule preuve de compatibilité).
3. Importer le personnel (CSV/Excel) avec la correspondance `pointeuse` + `id_pointeuse`.
4. Créer les comptes utilisateurs et leurs rôles/périmètres (`/api/users/`).

## Mode simulation (sans pointeuse)
```bash
docker compose exec web python manage.py seed_demo          # données synthétiques
docker compose exec web python manage.py seed_demo --clear  # les supprimer
```
Les pointages simulés appartiennent à un appareil désactivé « [SIMULATION] … » : ils ne prouvent rien sur la connexion aux vrais appareils.

## Mise à jour
```bash
deploy/backup.sh && git pull && docker compose up -d --build   # les migrations s'appliquent au démarrage
```

## Sauvegarde / restauration
`BACKUP_PASSPHRASE=… deploy/backup.sh` (archive chiffrée AES-256, 30 dernières conservées) ; `deploy/restore.sh <fichier>` (destructif, confirmation demandée). Tester la restauration régulièrement, conserver la phrase de passe hors du serveur, copier les sauvegardes hors site. Sauvegarder aussi `DEVICE_SECRET_KEY` : sans elle, les clés de communication des appareils sont illisibles.

## Supervision
Logs : `docker compose logs -f web worker beat`. Pointeuses : page « Pointeuses » et rapport « État des pointeuses ». Un appareil en échec est réessayé automatiquement (délais croissants) puis à chaque cycle planifié ; la mémoire de l'appareil n'est jamais effacée.
