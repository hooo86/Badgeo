# API REST

Base : `/api/`. Authentification : `POST /api/auth/token/` (`username`, `password`) → `{"token"}`, puis `Authorization: Token <jeton>`. 5 tentatives/minute. Pagination : `?page=` (50 par page), recherche `?search=`, tri `?ordering=`.

| Endpoint | Méthodes | Rôles (lecture / écriture) |
|---|---|---|
| `whoami/` | GET | tout utilisateur connecté |
| `devices/` (+ `{id}/test_connection/`, `{id}/sync/`), `sync-logs/` | CRUD / GET | sysadmin, admin pointeuses, RH / sysadmin, admin pointeuses |
| `device-users/` | CRUD | correspondance identifiant pointeuse ↔ employé |
| `employees/` (+ `import/`, `export/`) | CRUD | tous (périmètre) / RH |
| `org-units/`, `shifts/`, `rotations/`, `shift-assignments/`, `holidays/` | CRUD | tous / sysadmin, responsable RH |
| `leaves/` | CRUD | tous (périmètre) / RH |
| `punches/` | GET | tous (périmètre) ; filtres `device`, `employee`, `source`, `timestamp__gte/lte` |
| `attendance-days/` (+ `recompute/`) | GET | tous (périmètre) ; filtres `work_date__gte/lte`, `status__in`, `employee` |
| `corrections/` (+ `{id}/validate/`, `{id}/reject/`) | GET, POST | lecture RH/périmètre ; création RH ; validation responsable RH/sysadmin |
| `dashboard/` | GET | rôles « staff », limité au périmètre |
| `reports/<nom>/?from&to&fmt=json\|csv\|xlsx\|pdf` | GET | rôles « staff » ; noms : `daily monthly late absences early-leave hours overtime anomalies raw-punches corrections devices` |
| `users/`, `audit-logs/` | CRUD / GET | sysadmin / sysadmin, responsable RH |
| `me/`, `me/punch/`, `me/history/`, `me/planning/` | GET, POST | compte lié à un employé (application mobile) |

Codes d'erreur : `400` données invalides (corps `{"champ": ["message"]}` ou `{"detail": "…"}`), `401` non authentifié, `403` rôle/périmètre insuffisant, `404` introuvable, `405` méthode interdite (ex. modifier une correction), `429` limite de tentatives ou double pointage mobile.
Les accès aux rapports, exports, validations et connexions sont journalisés (`audit-logs/`).
