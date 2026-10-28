# Analyse de compatibilité, architecture et plan

## 1. Compatibilité ZKTeco / UNIS (Phase 1)

Les points marqués **[vérifié]** viennent de sources publiques consultées ; **[à confirmer]** exige l'appareil réel ou la documentation du fabricant.

| Voie | Principe | Statut |
|---|---|---|
| ZK « socket » (TCP/UDP, port 4370 par défaut, clé de communication) | L'application se connecte à l'appareil. Bibliothèque communautaire [pyzk](https://github.com/fananimi/pyzk) (`get_attendance`, `get_time`, `get_serialnumber`). | Documentée **[vérifié]**. Aucune liste officielle de modèles compatibles : à tester modèle par modèle. |
| ADMS / PUSH SDK (HTTP, `/iclock/cdata`, `/iclock/getrequest`) | L'appareil se connecte au serveur et envoie ses pointages. Utile pour les firmwares récents ou les appareils derrière un NAT. Voir le [document PUSH SDK](https://cdn.tvc.mx/media/92189/General-Introduction-of-PUSH-SDK-Protocol.pdf). | Protocole répandu (ZKTeco, eSSL, Anviz) **[vérifié]**. Connecteur à écrire (Phase 3b). |
| SDK Windows ZKTeco (COM `zkemkeyper`) | Bibliothèque propriétaire, Windows uniquement. | Non retenu : incompatible avec un déploiement Linux/Docker. |
| UNIS | Aucune source consultée ne confirme son protocole. Selon le modèle : protocole ZK, ADMS, ou SDK/HTTP propre. | **[à confirmer]** : modèle exact, firmware, menu « Réseau / Serveur cloud / ADMS », documentation fabricant. |

Contraintes réseau : accès IP de l'appareil depuis le serveur (même VLAN ou routage), port 4370 TCP ouvert pour le mode socket ; pour ADMS, l'appareil doit joindre le serveur (port HTTP). IP fixe ou réservation DHCP. Heure de l'appareil à régler (NTP si disponible) : les horodatages sont naïfs, interprétés dans le fuseau configuré par appareil.

**Informations à me fournir** : modèles exacts et firmware, IP/port de chaque appareil, clé de communication éventuelle, menu serveur/ADMS disponible, un export de test. Sans cela, aucune connexion UNIS ne sera déclarée fonctionnelle.

## 2. Architecture définitive

- **Backend** Django + DRF ; PostgreSQL ; Celery + Redis (worker + beat).
- **Adaptateurs** (`apps/devices/adapters/`) : interface `BaseAdapter` (`test`, `fetch_punches`), enregistrés dans un registre `ADAPTERS`. Ajouter un modèle = un fichier + une ligne, sans toucher au cœur. Adaptateurs prévus : `zkteco` (socket), `adms` (réception HTTP), `unis` (après identification).
- **Séparation des couches** : événements bruts (immuables) → moteur de présence (calcul, rejouable) → corrections (couche distincte, jamais d'écrasement) → rapports.
- **Frontend** React + TypeScript (Vite), i18n prévu (français par défaut).
- **Sécurité** : jetons API pour le prototype, puis sessions sécurisées + limitation des tentatives, rôles/périmètres, journal d'audit, chiffrement des secrets d'appareil (Phase 2), HTTPS via reverse proxy en production.
- **Biométrie** : seuls les événements de pointage sont lus ; aucun gabarit d'empreinte ou image faciale n'est récupéré.

## 3. Schéma de données (cible)

- `org_unit(id, parent, kind[structure|direction|service|departement], name)`
- `employee(uid, matricule UNIQUE, nom, prénom, org_unit, fonction, date_recrutement, statut[actif|suspendu|sorti])`
- `device(uid, name, vendor, model, ip, port, protocol, serial, timezone, secret_chiffré, status, last_seen, last_sync, events_total…)`
- `device_user_map(employee, device, device_user_id)` UNIQUE(device, device_user_id) + historique de validité
- `sync_run(device, trigger, started, finished, fetched, created, duplicates, errors, error)`
- `raw_punch(uid, device, device_user_id, ts_utc, ts_local_naive, punch_type, verify_mode, native_id, fetched_at, process_status, duplicate_of)` UNIQUE(device, device_user_id, ts) ; jamais supprimé
- `shift(…)`, `shift_period(horaire, début, fin_après_minuit, pause, tolérance, arrivée_min/max, durée_théorique)`, `shift_assignment(cible[employé|org_unit], shift, valid_from, valid_to)`, `rotation`, `holiday`
- `leave(employee, type[congé|permission|mission|arrêt|repos], from, to, justifié)`
- `attendance_day(employee, work_date, first_in, last_out, late_min, early_leave_min, presence_min, worked_min, overtime_min, status, anomalies[], computed_version)`
- `correction(attendance_day, valeur_initiale, valeur_corrigée, motif OBLIGATOIRE, auteur, date, statut[en_attente|validée|rejetée], validé_par)`
- `audit_log(user, action, objet, avant, après, ip, date)` ; `user`, `role`, `user_scope(user, org_unit)`

## 4. Arborescence

```
backend/  config/ (settings, celery, urls)
          apps/core · accounts · orgs · employees · devices(adapters/, services, tasks)
               · attendance(raw, engine) · schedules · leaves · corrections · reports · audit
frontend/ src/ (api.ts, pages/, components/, i18n/)
docs/  deploy/ (backup.sh, restore.sh, nginx.conf)  docker-compose.yml
```

## 5. Plan

| Phase | Contenu | État |
|---|---|---|
| 1 | Analyse protocoles | Fait (voie socket ZK documentée ; UNIS à confirmer) |
| 2 | Base de données, auth, rôles, audit, chiffrement des secrets | Fait (voir README) ; restent : MFA, expiration/rotation des jetons, UI de gestion des utilisateurs |
| 3 | Appareils, test IP, synchro idempotente, reprise | Prototype fait, non testé sur appareil réel ; incrémental, ADMS, doublons logiques à faire |
| 4 | Personnel, structures, horaires, import/export | À faire |
| 5 | Moteur de présence | À faire |
| 6 | Anomalies et corrections | À faire |
| 7 | Tableau de bord, rapports, exports | À faire |
| 8 | Tests, sécurité, sauvegarde, documentation | Partiel (3 tests unitaires simulés) |

## 6. Prototype livré

Ajouter une pointeuse, tester sa connexion (diagnostic TCP puis protocole), afficher son état, lancer une synchronisation. **Tests : uniquement simulés.** Aucune pointeuse réelle n'a été jointe.

Lancement local :
```bash
cd backend && pip install -r requirements.txt && python manage.py migrate && python manage.py createsuperuser && python manage.py runserver
cd frontend && npm install && npm run dev
```
