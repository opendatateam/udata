# Follow et notifications : ce qu'il reste à trancher

Le nouveau système de préférences est en place côté API. Il sait déjà, pour une famille
de notifications donnée :

- couper ou activer sur un objet précis, sur une organisation, ou partout
- traiter la cloche et le mail indépendamment
- regrouper les mails en résumé quotidien ou hebdomadaire (réglage par personne)

Ce qu'il ne sait pas encore, c'est ce qu'un « favori » doit déclencher. Aujourd'hui les
follows n'envoient rien du tout. Voici ce qu'on pense, et les questions qu'on a pour toi.

## Suivre une organisation

Ce qu'on pense : on veut les nouveaux objets publiés par cette organisation (jeux de
données, réutilisations, API). Le volume est raisonnable, même pour un gros producteur.

Confirmé côté technique : on peut couper les notifications d'une organisation suivie
sans se désabonner, et séparément pour la cloche et le mail.

Ce qui manque : aucun événement « nouvel objet publié » n'existe aujourd'hui, il faut le
créer.

Questions :
- est-ce qu'on notifie aussi quand un objet est dépublié ou supprimé ?
- est-ce qu'un jeu de données créé en privé puis publié compte comme un nouvel objet ?

## Suivre un jeu de données

Ce qu'on pense : les nouvelles ressources, sûr. Et les remplacements de fichier,
sans doute.

Questions :
- est-ce que les modifications de métadonnées sont utiles (titre, description, licence,
  couverture temporelle, fréquence) ? Si oui, lesquelles méritent une notification et
  lesquelles sont du bruit ?
- est-ce qu'une ressource supprimée se notifie ?
- est-ce qu'un fichier remplacé sans changement de nom compte, même si rien d'autre ne
  bouge sur la page ?

## Suivre une réutilisation, suivre une API

On ne voit rien à notifier là-dessus.

Question : est-ce que les modifications de métadonnées seraient utiles ? Si la réponse
est non, est-ce qu'on garde le bouton « suivre » sur ces pages ? Il existe aujourd'hui et
ne produit rien.

## Suivre un utilisateur

Ce qu'on pense : ses nouveaux objets.

Questions :
- est-ce qu'on veut aussi ses discussions ? Pas sûr.
- est-ce qu'on veut les réutilisations qu'il publie sur les données des autres ?

Le bouton n'existe pas côté front aujourd'hui, seulement dans l'API.

## Les discussions d'un objet

C'est le point le plus ouvert. Suivre un jeu de données populaire et recevoir toutes ses
discussions, ça peut faire beaucoup, et ce n'est pas forcément ce qu'on cherche en
mettant un favori.

Question : est-ce que suivre un objet doit donner ses discussions, oui ou non ?

Ce qu'on propose plutôt : séparer les deux gestes. Un bouton « Suivre les discussions de
cet objet » indépendant du favori, et le favori garde les modifications de l'objet. Deux
intentions différentes, deux boutons, chacun débrayable de son côté.

Le nouveau système sait déjà porter un réglage à ce niveau (une catégorie, un objet, un
canal). Il manque une chose : aujourd'hui il ne fait que filtrer une liste de
destinataires calculée par l'événement, il ne sait pas ajouter quelqu'un qui n'y était
pas. Un bouton d'abonnement explicite demande donc un développement en plus, pas juste
un réglage à exposer.

## Ce qu'il faut construire dans tous les cas

Quelle que soit la réponse aux questions ci-dessus :

- [ ] les événements de modification (nouvelle ressource, fichier remplacé, nouvel objet
      dans une organisation) n'existent pas, il faut les créer
- [ ] l'abonnement explicite (s'ajouter comme destinataire sans être membre ni auteur)
- [ ] la création d'une réutilisation ou d'une API notifie de manière synchrone
      aujourd'hui, à passer en tâche de fond avant d'y ajouter des abonnés
- [ ] les notifications sont écrites une par une, et chaque mail ouvre sa propre
      connexion SMTP. Ça tient pour une organisation, pas pour un objet à plusieurs
      milliers d'abonnés

## Le chiffre qui manque

On ne sait pas combien de personnes suivent réellement les objets les plus suivis. C'est
public et ça se vérifie :

```
curl -s "https://www.data.gouv.fr/api/1/datasets/?sort=-followers&page_size=20" \
  | jq '.data[] | {title, followers: .metrics.followers}'
```

Si le maximum est de quelques centaines, les deux derniers points ci-dessus sont
théoriques. S'il monte à plusieurs milliers, il faut les traiter avant d'activer quoi que
ce soit.
