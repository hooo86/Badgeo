# Licences et sauvegardes

## Licences (édition locale)
- **Clé signée (Ed25519), vérifiée hors ligne.** Le logiciel ne contient que la clé publique ; sans la clé privée de l'éditeur, impossible de fabriquer une clé.
- **Liée au poste** : code d'installation `BDG-XXXX-XXXX-XXXX` dérivé de l'identifiant de la machine (MachineGuid Windows). Une installation copiée ailleurs demande une nouvelle clé.
- **Contenu de la clé** : client, modules (`mobile`, `reports`, `leaves` ; le socle — personnel, pointeuses, présences, tableau de bord — est toujours inclus), plafond d'employés actifs, plafond de pointeuses, date de fin.
- **Clé d'essai** (code `*`) : valable sur tous les postes, date de fin obligatoire ; réservée aux versions de test.
- **Application** : sans licence valable, l'API répond 402 (sauf activation et connexion) ; licence expirée : lecture seule (402 sur toute écriture, sauf connexion, licence et sauvegardes) ; module non vendu : 403 ; plafonds appliqués à la création (interface, API, import, admin). Reculer l'horloge ne prolonge pas une licence (dernière date vue conservée).
- Commandes éditeur : `generer_cles_licence` (une fois), `emettre_licence`. Interface : « Licence et compte ». Variable `BADGEO_LICENCE_REQUISE=1` pour exiger la licence hors Windows.

## Sauvegardes (menu « Sauvegardes », administrateur système)
- Archive `.badgeo` (zip : `manifest.json` + `data.json`) indépendante du moteur de base : SQLite ↔ PostgreSQL.
- Contenu : toutes les données métier. **Exclus** : sessions, jetons, licence (restaurer ne remplace pas la licence) et **journal d'audit** (jamais remonté dans le temps). La mémoire des pointeuses n'est jamais touchée.
- Chiffrement AES (Fernet + scrypt) si `BADGEO_BACKUP_PASSPHRASE` est défini. Le secret des pointeuses reste chiffré par `DEVICE_SECRET_KEY` : **sauvegardez aussi cette clé** (Windows : `C:\ProgramData\Badgeo\cle_secrets_pointeuses.txt`).
- Manuelle, automatique (une par jour à l'heure choisie, N conservées), copie vers un autre dossier ou disque, téléchargement, import d'un fichier.
- **Restauration** : somme de contrôle vérifiée, version compatible, confirmation en tapant `RESTAURER`, sauvegarde « avant restauration » créée d'abord, tout dans une transaction (échec = rien de modifié). Tous les utilisateurs doivent se reconnecter.
- Sur Windows, avant chaque mise à jour, copie du fichier de base dans `sauvegardes\avant-mise-a-jour`.
