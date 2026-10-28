# Règles de calcul des présences

Le moteur (`backend/apps/attendance/engine.py`) est indépendant du fabricant : il ne voit que des horodatages. Les pointages bruts ne sont jamais modifiés ; les journées (`AttendanceDay`) sont recalculables à tout moment.

| Sujet | Règle |
|---|---|
| Doublons | Un pointage à moins de `PUNCH_DEDUP_MINUTES` (2 par défaut) du précédent est ignoré dans le calcul (anomalie `duplicate_punch`) ; la donnée brute reste intacte. |
| Rattachement à une journée | Un pointage tôt le matin appartient à la veille si l'horaire de la veille traverse minuit et que le pointage est au plus 4 h après sa fin. |
| Retard | Si l'arrivée dépasse l'heure prévue + tolérance, le retard compté va de l'heure prévue à l'arrivée. Horaire variable : retard au-delà de l'heure maximale d'arrivée. |
| Départ anticipé | Écart avec l'heure de fin prévue, au-delà de la tolérance de départ. |
| Présence / travail | Présence = dernier − premier pointage. Travail = somme des paires entrée/sortie si ≥ 4 pointages, sinon présence − pause théorique. |
| Heures sup. | Potentielles uniquement : temps après l'heure de fin (ou au-delà de la durée théorique en horaire variable), au-dessus d'un seuil (30 min par défaut). À valider par les RH. |
| Pointage unique | Journée en cours si la fenêtre n'est pas close ; sinon `incomplete` + `missing_out` (ou `missing_in` si le pointage est dans la seconde moitié de l'horaire). |
| Nombre impair | `incomplete` + `odd_punches`. |
| Aucun pointage un jour travaillé | `no_punch` (« sans pointage »), **pas** une absence. Devient `absent` seulement si `NO_PUNCH_BECOMES_ABSENCE=1` et la journée est close. |
| Congés, missions, arrêts, repos | Statut propre, avec indicateur « justifié ». Permission partielle : couvre un retard ou un départ anticipé dans sa plage. |
| Jours fériés / repos | Statut `holiday` / `rest` ; un pointage ces jours-là est signalé et compté en heures sup. potentielles. |
| Affectation d'horaire | Employé > unité la plus proche > unités parentes ; à égalité, la plus récente `valid_from`. Une rotation donne un horaire ou un repos selon le jour du cycle. |
| Plusieurs appareils | Tous les pointages de l'employé sont fusionnés, quel que soit l'appareil. |
| Corrections | Jamais d'écrasement : une correction validée ajoute un pointage `manual` ou force un statut ; la valeur initiale, la nouvelle, l'auteur, le motif et le valideur sont conservés. L'auteur ne peut pas valider sa propre correction. |

Modifier un horaire ne recalcule pas automatiquement le passé : lancer `POST /api/attendance-days/recompute/` (période ≤ 92 jours).
