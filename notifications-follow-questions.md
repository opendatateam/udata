- quand tu édites un jeu de données on t'abonne auto -> toast avec opt-out
https://www.figma.com/design/FXdvJqrMlsEq0G65qXl27I/%E2%9C%89%EF%B8%8F-Email-et-notifications?node-id=6-16337&t=QyhJTLHP9Lh5dmm0-4

# Favoris et notifications : ce qu'il reste à trancher

Le nouveau système de préférences est en place côté API. Il sait déjà, pour une famille
de notifications donnée :

- couper ou activer sur un objet précis, sur une organisation, ou partout
- traiter la cloche et le mail indépendamment
- regrouper les mails en résumé quotidien ou hebdomadaire (réglage par personne)
- abonner quelqu'un à un objet dont il n'est ni membre, ni auteur, ni participant

Ce qu'il ne sait pas encore, c'est ce qu'un favori doit déclencher. Aujourd'hui les
favoris n'envoient rien du tout. Voici ce qu'on pense, et les questions qu'on a pour toi.

## Favori et abonnement : deux gestes ou un seul ?

C'est la question qui commande toutes les autres, parce qu'elle décide de ce que
l'étoile veut dire.

Côté technique les deux sont déjà séparés : le favori est un objet à lui (celui
qu'utilise le bouton « Ajouter aux favoris »), l'abonnement en est un autre. Rien ne les
lie, et la maquette leur donne déjà deux entrées de menu distinctes, « Favoris » et
« Gestion des alertes ».

Trois façons de les articuler :

1. ~~Le favori notifie. Une seule étoile, un seul geste. Mais on ne peut plus mettre de
   côté sans être prévenu, ni être prévenu sans mettre en favori.~~
2. ~~Deux gestes indépendants. L'étoile pour ranger, un second bouton pour être prévenu.~~
3. Le favori notifie les modifications de l'objet, et un bouton séparé « Suivre les
   discussions » pour ce qui fait du volume.

On penche pour la troisième : elle donne un sens au favori au lieu d'en faire un
marque-page inerte, et elle isole ce qui fait vraiment du bruit.

Question : est-ce que « favori » doit rester le seul mot côté produit, ou est-ce qu'on
assume deux verbes différents ?

## Mettre une organisation en favori

Ce qu'on pense : on veut les nouveaux objets publiés par cette organisation (jeux de
données, réutilisations, API). Le volume est raisonnable, même pour un gros producteur.

Confirmé côté technique : on peut couper les notifications d'une organisation mise en
favori sans la retirer des favoris, et séparément pour la cloche et le mail.

Ce qui manque : aucun événement « nouvel objet publié » n'existe aujourd'hui, il faut le
créer.

Questions :
- est-ce qu'on notifie aussi quand un objet est dépublié ou supprimé ? Non
- est-ce qu'un jeu de données créé en privé puis publié compte comme un nouvel objet ? Oui

## Mettre un jeu de données en favori

Ce qu'on pense : les nouvelles ressources, sûr. Et les remplacements de fichier,
sans doute.

Questions :
- est-ce que les modifications de métadonnées sont utiles (titre, description, licence,
  couverture temporelle, fréquence) ? Si oui, lesquelles méritent une notification et
  lesquelles sont du bruit ? non
- est-ce qu'une ressource supprimée se notifie ? oui
- est-ce qu'un fichier remplacé sans changement de nom compte, même si rien d'autre ne
  bouge sur la page ? oui

## Mettre une réutilisation ou une API en favori

On ne voit rien à notifier là-dessus.

Question : est-ce que les modifications de métadonnées seraient utiles ? non
Si la réponse est non, est-ce qu'on garde le bouton sur ces pages ? oui

## Mettre un utilisateur en favori

Ce qu'on pense : ses nouveaux objets.

Questions :
- est-ce qu'on veut aussi ses discussions ? non
- est-ce qu'on veut les réutilisations qu'il publie sur les données des autres ? oui

Le bouton n'existe pas côté front aujourd'hui, seulement dans l'API.

## Les discussions d'un objet

C'est le point le plus ouvert. Mettre en favori un jeu de données populaire et recevoir
toutes ses discussions, ça peut faire beaucoup, et ce n'est pas forcément ce qu'on
cherche en cliquant sur l'étoile.

Question : est-ce que mettre un objet en favori doit donner ses discussions, oui ou non ? non


abonnement sur toutes les notifications -> création ? ou création et réponses ? juste création pour le moment

Si la réponse est non, le bouton séparé de la troisième option plus haut répond au
besoin. Côté technique il ne demande rien de nouveau : c'est le même abonnement
explicite que celui qui vient d'être construit. non

## Ce qu'il faut construire dans tous les cas

- [x] l'abonnement explicite (s'ajouter comme destinataire sans être membre ni auteur)
- [ ] les événements de modification (nouvelle ressource, fichier remplacé, nouvel objet
      dans une organisation) n'existent pas, il faut les créer
- [ ] la création d'une réutilisation ou d'une API notifie de manière synchrone
      aujourd'hui, à passer en tâche de fond avant d'y ajouter des abonnés
- [ ] les notifications sont écrites une par une, et chaque mail ouvre sa propre
      connexion SMTP. Tenable aux volumes actuels (voir plus bas), à reprendre quand
      même

## Le volume réel

Mesuré le 17 septembre 2026 sur l'API publique, sur les objets les plus mis en favori :

| | Record | Suivants |
|---|---|---|
| Jeux de données (73 900 au total) | 201 (Sirene) | 138, 95, 80, 72 |
| Réutilisations | 324 | 258, 217, 213, 169 |
| Organisations | 662 (Insee) | 429, 375, 359, 299 |

On est donc dans les centaines, pas dans les milliers, et la décroissance est rapide dès
le deuxième objet. C'est l'ordre de grandeur que le système encaisse déjà aujourd'hui
pour une organisation à plusieurs centaines de membres.

Ça change la priorité de deux points ci-dessus : grouper les écritures et les envois
reste souhaitable, mais ce n'est plus un préalable. Passer la création de réutilisation
et d'API en tâche de fond le reste, en revanche : 201 destinataires servis pendant la
requête HTTP de celui qui publie, c'est un timeout pour quelqu'un qui n'a rien demandé.
