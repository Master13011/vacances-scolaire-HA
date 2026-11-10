# Tests — Intégration Vacances Scolaires pour Home Assistant

Ce document décrit les tests automatisés de l'intégration `vacances_scolaires`.
Ils sont placés dans le dossier `tests/` et s'exécutent avec **pytest** et `pytest-homeassistant-custom-component`.

## Principes

- **Aucun accès réseau** : l'API Éducation nationale est simulée (fausse session HTTP pour `test_api.py`, remplacement de `async_fetch_records` pour les autres tests).
- Les dates des enregistrements de test sont calculées par rapport à « maintenant » (`make_record`), ou figées avec `freezegun` quand une date précise est nécessaire : les tests ne dépendent pas du calendrier réel.
- Une fixture `autouse` (`conftest.py`) active le chargement de l'intégration personnalisée dans chaque test.
- Helpers communs dans `tests/common.py` : `make_record`, `make_entry` (localisation Paris), `make_zone_entry` (zone).
- Exécution automatique via GitHub Actions (`.github/workflows/tests.yml`).

## Lancer les tests

```bash
pip install -r requirements.txt
pytest -q
```

## Contenu des tests

### `test_api.py` — client API

| Domaine | Ce qui est vérifié |
|---|---|
| Résultats | `async_fetch_records` renvoie la liste `results`. |
| Requête localisation / zone | Paramètres `where`, `order_by`, `limit`, `refine` ; `refine = location:Paris` ou `zones:Zone A` ; tri `start_date ASC` ; limite par défaut 2 et limite personnalisable ; filtre `end_date>=date'…'`. |
| Sécurité | Une valeur malveillante (`Paris&where=1=1&limit=999`) reste confinée dans le paramètre `refine` et n'est jamais ajoutée à l'URL ; la vérification SSL n'est pas désactivée. |
| Erreurs | Type de configuration inconnu → `VacancesScolairesError` ; aucun résultat, clé `results` absente ou HTTP 400 → `VacancesScolairesNoDataError` ; HTTP 500, erreur réseau, timeout ou JSON invalide → `VacancesScolairesApiError`. |
| Distinction des erreurs | `NoDataError` et `ApiError` ne dérivent pas l'une de l'autre (le config flow les signale différemment). |
| `async_fetch_locations` | Dédoublonnage, nettoyage (valeurs `None` ou vides ignorées) et tri alphabétique ; requête `select/group_by/limit=100` ; liste vide → `NoDataError` ; HTTP 500 → `ApiError`. |
| `async_fetch_zones` | Zones officielles en premier dans l'ordre (Zone A, B, C, Corse, Réunion…) puis zones inconnues ; requête `select/group_by/limit=100` ; erreur de connexion → `ApiError`. |

### `test_config_flow.py` — assistant de configuration

| Domaine | Ce qui est vérifié |
|---|---|
| Localisation | La liste déroulante est alimentée par l'API ; création de l'entrée (titre, données, `unique_id = location_paris`) ; repli sur un champ texte libre (valeur nettoyée de ses espaces) si la liste est indisponible. |
| Erreurs de saisie | Localisation introuvable → erreur `location_not_found` ; API indisponible pendant la validation → erreur `cannot_connect` ; le formulaire se rétablit et aboutit après une erreur. |
| Doublons | Même localisation refusée (`already_configured`), y compris en ignorant la casse, les accents et les espaces (`"  PARIS "`). |
| Validation | Intervalle hors plage (0, -1, 169) refusé ; localisation hors de la liste refusée. |
| Zone | Liste alimentée par l'API ; création de l'entrée (`unique_id = zone_zone b`) ; repli sur la liste intégrée `ZONE_OPTIONS` si l'API est indisponible ; doublon refusé ; zone inconnue refusée ; intervalle hors plage refusé. |
| Étape initiale | Aucune option `verify_ssl` n'est proposée. |

### `test_options_flow.py` — options

| Test | Ce qui est vérifié |
|---|---|
| Affichage | Le formulaire propose l'intervalle actuel (6 h) ; un intervalle stocké invalide (0) est ramené à 1. |
| Modification | Passer de 12 h à 24 h enregistre l'option et **recharge automatiquement** l'entrée avec le nouvel intervalle. |
| Validation | Intervalles 0, -3 et 169 refusés. |

### `test_init.py` — installation, requêtes, entités

| Domaine | Ce qui est vérifié |
|---|---|
| Cycle de vie | Installation puis déchargement ; `SETUP_RETRY` si l'API est injoignable ou ne renvoie aucune donnée. |
| Plateformes | Sans calendrier : 3 capteurs et aucun calendrier. |
| Requêtes | Une entrée « localisation » interroge `("location", "Paris")` ; une entrée « zone » interroge `("zone", "Zone C")`. |
| Rétrocompatibilité | Les `unique_id`, `entity_id` et noms historiques sont conservés (ex. `sensor.vacances_scolaires_paris`, `…_aujourd_hui_paris`, `…_demain_paris`, `sensor.vacances_scolaires_zone_c`). |
| Appareil | Les entités appartiennent à l'appareil « Vacances Scolaires ». |
| États | `Zone C - Holidays` / `Zone C - Work` ; capteurs Aujourd'hui/Demain : `En vacances` / `Pas en vacances`. |
| Attributs | `description`, `location`, `zone`, `année_scolaire`, `en_vacances` (vrai ou faux), dates en français. |
| Choix de l'enregistrement | Priorité aux « Élèves », puis à l'enregistrement générique (`-`), sinon au premier de la liste. |
| Intervalle de mise à jour | Lu depuis les données, les options l'emportent ; valeur 0 ramenée à 1 h, valeur trop grande plafonnée à 168 h. |
| Conversion de date | `convert_to_iso_format` convertit une date française ; chaîne vide si le format est invalide. |

### `test_coordinator.py` — coordinateur

| Domaine | Ce qui est vérifié |
|---|---|
| Traduction des mois | Les 12 mois anglais sont traduits en français ; le texte déjà en français ou vide est laissé tel quel. |
| Fuseaux horaires | Fuseau propre à chaque territoire d'outre-mer (Guadeloupe, Guyane, Martinique, Mayotte, Nouvelle-Calédonie, Polynésie, Réunion, Saint-Pierre-et-Miquelon, Wallis-et-Futuna), vérifié dans la base tz ; `Europe/Paris` pour les autres. |
| Bornes de période | Veille du début : hors vacances ; premier jour, jours intermédiaires, dernier jour (journée entière) : en vacances ; lendemain de la fin : hors vacances. |
| Données calculées | Zone de l'enregistrement utilisée dans l'état (`Corse - Holidays`) ; dates formatées en français en conservant l'heure UTC de l'API ; ensemble exact des clés renvoyées ; champs optionnels absents → `None`. |
| Erreurs | Type de configuration inconnu → `UpdateFailed` sans appel API ; erreurs `ApiError` et `NoDataError` → `UpdateFailed`. |

### `test_calendar.py` — plateforme calendrier

| Test | Ce qui est vérifié |
|---|---|
| Création | Le calendrier n'est créé que si demandé (`calendar.vacances_scolaires_paris`, nom attendu). |
| État | `on` pendant les vacances (avec le message), `off` en dehors. |
| Appareil | Le calendrier et les capteurs partagent le même appareil. |

### `test_calendar_events.py` — événements du calendrier

| Domaine | Ce qui est vérifié |
|---|---|
| Identité | `unique_id`, nom, `has_entity_name`, appareil. |
| Événement courant | Résumé, début < fin, fuseau Europe/Paris ; aucun événement hors vacances ; fuseau propre aux territoires d'outre-mer (Guadeloupe, Réunion, Polynésie). |
| Plage de dates | Événement renvoyé quand la plage est incluse dans les vacances, chevauche le début ou la fin, ou les contient ; liste vide en dehors ou hors vacances. |
| Lecture seule | Création, modification et suppression d'événement lèvent `NotImplementedError`. |
| Conversion | `convert_to_iso_format` sur des dates françaises. |

### `test_sensor.py` — capteurs

| Domaine | Ce qui est vérifié |
|---|---|
| `get_entry_target` | Cible d'une entrée localisation ou zone ; localisation par défaut si le type est absent ; `Unknown` si le nom est absent. |
| Identité | `unique_id` et noms historiques inchangés (localisation et zone) ; appareil et attribution communs. |
| Capteur principal | État et attributs exacts ; capteurs vides si les données sont `None` ou `{}`. |
| Aujourd'hui / Demain | Pendant les vacances, à la veille du dernier jour, la veille du premier jour, avant et après la période ; suivent les nouvelles données du coordinateur ; `None` si les dates sont inutilisables. |
| Mise à jour de minuit | Un rafraîchissement est programmé chaque jour à 00:00:05 ; il réécrit l'état du capteur. |

### `test_sensor_day_transitions.py` — bascule des capteurs Aujourd'hui / Demain

Le temps est figé (`freezegun`) autour des bornes des vacances (du 8 novembre 00:00 au 14 novembre 22:00 2026).

| Domaine | Ce qui est vérifié |
|---|---|
| Demain, début des vacances | `Pas en vacances` à J-2 ; `En vacances` dès que « demain » atteint le début (bascule exacte à J-1 00:00:00) et pendant toute la journée de la veille. |
| Demain, fin des vacances | `En vacances` tant que « demain » reste dans la période (jusqu'à l'instant exact de fin) ; `Pas en vacances` quand les vacances sont terminées demain. |
| Aujourd'hui, début des vacances | `Pas en vacances` à 23:59:59 la veille ; `En vacances` dès 00:00:00 le jour de début. |
| Aujourd'hui, fin des vacances | `En vacances` jusqu'à l'instant exact de fin ; `Pas en vacances` une seconde plus tard et le lendemain. |
| Cycle complet | Les deux capteurs ensemble : (Pas, Pas) → (Pas, En) la veille → (En, En) le jour J → (En, Pas) le dernier jour → (Pas, Pas) après. |
| Dates relatives | Même scénario avec des vacances construites à partir de la date courante (indépendant du calendrier). |
| Minuit | Une même instance change de valeur après minuit ; le rafraîchissement de 00:00:05 réécrit l'état ; bascule aussi à la fin des vacances. |
| Prochaines vacances | Quand le coordinateur fournit la période suivante (ex. Noël), les deux capteurs suivent. |

### `test_util.py` — utilitaires

| Test | Ce qui est vérifié |
|---|---|
| `normalize_text` | Suppression des accents et de la casse (`Élèves` → `eleves`) ; `None` et chaîne vide → `""`. |
| `sanitize_update_interval` | Valeurs valides conservées (y compris `"24"`) ; 0 ou négatif → 1 ; 9999 → 168 ; valeur invalide (`None`, `"abc"`) → 12. |
