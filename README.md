# vacances-scolaire-HA
![Home Assistant](https://img.shields.io/badge/Home--Assistant-2025.8+-blue?logo=home-assistant)
![Custom Component](https://img.shields.io/badge/Custom%20Component-oui-orange)
![Licence MIT](https://img.shields.io/badge/Licence-MIT-green)

Intégration Vacances Scolaire FR pour Home Assistant

Forum App : https://forum.hacf.fr/t/integration-vacances-scolaires/58499

Cette intégration personnalisée pour Home Assistant permet aux utilisateurs de récupérer et d'afficher les périodes de vacances scolaires en fonction de leur localisation. Les utilisateurs peuvent configurer la localisation et l'intervalle de mise à jour directement via l'interface de Home Assistant, offrant ainsi une flexibilité maximale. L'intégration utilise des données ouvertes du ministère de l'Éducation français pour fournir des informations précises sur les vacances scolaires. Compatible avec HACS, elle facilite l'installation et la mise à jour.

## Fonctionnalités

- **Affichage des vacances scolaires** : Montre les vacances en cours ou la prochaine pour une localisation spécifique par zone et/ou ville.
     - Zone académique métropole
     - Zone académique pour la Corse, les départements d'outre-mer et les collectivités d'outre-mer
- **Indicateur booléen en_vacances** : Indique si l'on est en vacances. (true ou false)
- **Localisation personnalisable** : Permet de choisir la localisation pour laquelle on souhaite obtenir les informations sur les vacances scolaires.
- **Intervalle de mise à jour configurable** : Offre la possibilité de définir la fréquence de mise à jour des données.
- **Données officielles** : Utilise l'API officielle du ministère de l'Éducation française pour des informations précises et à jour.
- **Attributs détaillés** : Fournit des informations supplémentaires telles que les dates de début et de fin des vacances.
- **Ajout calendrier** : Vous avez la possibilité d'ajouter un calendrier
- **Ajout capteur** : Vacances Scolaires Aujourd’Hui et Demain
  
## Installation

1. Assurez-vous que [HACS](https://hacs.xyz) est installé.

2. Ouvrez HACS.
   
3. Cherchez directement : vacances scolaire

Ou
   
3. Cliquez sur les trois points en haut à droite et choisissez "Dépôts personnalisés".

4. Ajoutez le dépôt :
   - URL : 'https://github.com/Master13011/vacances-scolaire-HA'
   - Type : Intégration

5. Cliquez sur "Ajouter".

6. Recherchez "Vacances Scolaires" dans les intégrations HACS et installez-la.

7. Redémarrez Home Assistant.

## Configuration

1. Allez dans Paramètres > Appareils et services dans Home Assistant.
2. Cliquez sur le bouton "+" pour ajouter une nouvelle intégration.
3. Recherchez "Vacances Scolaires" et sélectionnez-la.
4. Suivez les étapes de configuration :
   - Choisissez soit par la Ville, soit par la Zone
      - Ville : Choisissez la localisation (par exemple, "Aix-Marseille", "Paris", "Bordeaux", etc.)
           - Veuillez respecter le découpage des villes -> https://www.education.gouv.fr/calendrier-scolaire-100148
      - Zone : Choissisez la Zone (Zone A, Zone B, Zone C, Guyane, Nouvelle Calédonie, Wallis et Futuna, Saint Pierre et Miquelon, Polynésie, Mayotte, Martinique, Guadeloupe, Corse, Réunion)
   - Définissez l'intervalle de mise à jour en heures

![{258E39D5-FD11-412D-BC47-4C19B6FDA5B5}](https://github.com/user-attachments/assets/3b7d0038-141d-431a-b7c7-e056ff1b0815) 


## Utilisation

Une fois installée et configurée, l'intégration Vacances Scolaires ajoutera un capteur à votre instance Home Assistant. Ce capteur affichera les informations sur les vacances en cours pour la localisation spécifiée.

![{640F061F-260B-4A7D-846C-6729C9AE6583}](https://github.com/user-attachments/assets/f5737c24-8952-46e7-88d1-79caf85c2617)

![{2C967C88-7E4D-4A34-9704-10A08D9E3E14}](https://github.com/user-attachments/assets/83ed1c94-5efc-431e-8c35-289a8c8b10dd)

Le "state" retournera :

"Zone X - Holidays" ou "Zone X - Work"

## Contribution

Les contributions à ce projet sont les bienvenues. N'hésitez pas à soumettre des pull requests ou à ouvrir des issues pour des suggestions d'amélioration ou des rapports de bugs.
