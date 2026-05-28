# Challenge Amazon FBA

## Sequence de messages WhatsApp - Version 2.1

Base editoriale conservee depuis le document v2.

Objectif de cette version : ajouter seulement les nouveaux rappels, les remplacements explicitement demandes et les messages manquants.

## Matrice de travail

- Messages de base : conserves sur la base du document v2
- Remplacements cibles : `live_day2_attended`, `live_day3_attended`, `post_recap_registered_absent`, `post_recap_not_registered`
- Nouveaux messages : rappels H-10 / H+5, paiement H+2, temoignages, frein, closer

## live_day2_attended

- Type : Remplacement cible
- Timing : Jour 2, 2h avant le live
- Audience : Presents au Jour 1

Variables :
- {{1}} : Prenom
- {{2}} : Lien StreamYard Session 2
- {{3}} : Heure Session 2

```text
{{1}}, ta presence d'hier soir montre deja que tu es dans une vraie demarche.

Ce soir, on va encore plus loin.

Session 2 a {{3}} - le sujet : Construire Ton Business Amazon Pas a Pas

📹 {{2}}

Avant ce soir, dis-moi : qu'est-ce qui t'a le plus marque hier ?
```

Note : On conserve l'esprit du message v2 et on ajoute seulement la question demandee par le client.

## live_day3_attended

- Type : Remplacement cible
- Timing : Jour 3, 2h avant le live
- Audience : Presents au Jour 2

Variables :
- {{1}} : Prenom
- {{2}} : Lien StreamYard Session 3
- {{3}} : Heure Session 3

```text
{{1}}, ce soir, on arrive a la derniere session.

On se retrouve a {{3}} pour : Le Secret des Vendeurs a Succes sur Amazon

📹 {{2}}

Et avant ce soir, dis-moi : qu'est-ce qui t'a le plus marque dans la session d'hier ?
```

Note : On garde la base redactionnelle et on ajoute seulement la question contextuelle demandee.

## post_recap_registered_absent

- Type : Remplacement cible
- Timing : J+1
- Audience : Inscrits ayant suivi une partie du challenge

Variables :
- {{1}} : Prenom
- {{2}} : Replay Jour 1
- {{3}} : Replay Jour 2
- {{4}} : Replay Jour 3

```text
Bonjour {{1}} 👋

Comme promis, voici les replays des 3 jours du Challenge Amazon FBA :

🎥 Jour 1 : {{2}}
🎥 Jour 2 : {{3}}
🎥 Jour 3 : {{4}}

Prends le temps de regarder ce que tu as manque, puis dis-moi ce qui t'a le plus parle.
```

Note : Ce message remplace la logique 'reponds INFO' par un partage direct des replays.

## post_recap_not_registered

- Type : Remplacement cible
- Timing : J+1
- Audience : Aucun live suivi

Variables :
- {{1}} : Prenom
- {{2}} : Replay Jour 1
- {{3}} : Replay Jour 2
- {{4}} : Replay Jour 3

```text
Bonjour {{1}} 👋

Tu n'as peut-etre pas pu suivre les lives, donc je te laisse ici les replays des 3 jours :

🎥 Jour 1 : {{2}}
🎥 Jour 2 : {{3}}
🎥 Jour 3 : {{4}}

Si tu les regardes, reponds-moi simplement ici. Je veux savoir ce qui t'a le plus parle.
```

Note : On garde l'intention de rattrapage, avec un lien concret plutot qu'un CTA flou.

## live_day1_h10

- Type : Nouveau message
- Timing : Jour 1, 10 minutes avant
- Audience : Tous les inscrits actifs

Variables :
- {{1}} : Prenom
- {{2}} : Lien StreamYard Session 1

```text
Bonjour {{1}},

On demarre dans 10 minutes.

Voici ton lien d'acces :
{{2}}

A tout de suite.
```

## live_day1_hplus5

- Type : Nouveau message
- Timing : Jour 1, 5 minutes apres le debut
- Audience : Ceux qui n'ont pas clique ou ouvert le message precedent

Variables :
- {{1}} : Prenom
- {{2}} : Lien StreamYard Session 1

```text
Bonjour {{1}},

Le live a commence il y a 5 minutes.

Si tu comptais nous rejoindre, tu peux encore entrer ici :
{{2}}
```

## live_day2_h10

- Type : Nouveau message
- Timing : Jour 2, 10 minutes avant
- Audience : Tous les contacts cibles pour le Jour 2

Variables :
- {{1}} : Prenom
- {{2}} : Lien StreamYard Session 2

```text
Bonjour {{1}},

On demarre dans 10 minutes.

Voici ton lien pour la Session 2 :
{{2}}

A tout de suite.
```

## live_day2_hplus5

- Type : Nouveau message
- Timing : Jour 2, 5 minutes apres le debut
- Audience : Ceux qui n'ont pas clique ou ouvert le message precedent

Variables :
- {{1}} : Prenom
- {{2}} : Lien StreamYard Session 2

```text
Bonjour {{1}},

La Session 2 a commence il y a 5 minutes.

Tu peux encore nous rejoindre ici :
{{2}}
```

## live_day3_h10

- Type : Nouveau message
- Timing : Jour 3, 10 minutes avant
- Audience : Tous les contacts cibles pour le Jour 3

Variables :
- {{1}} : Prenom
- {{2}} : Lien StreamYard Session 3

```text
Bonjour {{1}},

Plus que 10 minutes avant la derniere session.

Voici ton lien :
{{2}}

A tout de suite.
```

## live_day3_hplus5

- Type : Nouveau message
- Timing : Jour 3, 5 minutes apres le debut
- Audience : Ceux qui n'ont pas clique ou ouvert le message precedent

Variables :
- {{1}} : Prenom
- {{2}} : Lien StreamYard Session 3

```text
Bonjour {{1}},

La derniere session a commence il y a 5 minutes.

Si tu veux encore nous rejoindre, c'est ici :
{{2}}
```

## live_day3_offer_hplus2

- Type : Nouveau message
- Timing : Jour 3, 2 heures apres le debut du live
- Audience : Contacts n'ayant pas encore paye

Variables :
- {{1}} : Prenom
- {{2}} : Lien de paiement

```text
Bonjour {{1}},

Comme promis pendant le direct, voici le lien pour rejoindre l'accompagnement :
{{2}}

Prends le temps de le lire tranquillement.

Et si tu veux qu'on echange avant de decider, reponds-moi ici.
```

Note : A arreter automatiquement pour les personnes qui ont deja pris la formation le jour meme.

## post_testimonials

- Type : Nouveau message
- Timing : Apres J+1
- Audience : Contacts encore actifs

Variables :
- {{1}} : Prenom

```text
Bonjour {{1}},

Je te partage deux retours de personnes qui sont passees a l'action apres le challenge :

[TEMOIGNAGE 1]

[TEMOIGNAGE 2]

Si tu veux qu'on voie si c'est possible pour toi aussi, reponds-moi ici.
```

Note : A completer avec les vrais temoignages transmis par le client.

## post_inaction_reason

- Type : Nouveau message
- Timing : Apres les temoignages
- Audience : Contacts qui n'ont toujours pas avance

Variables :
- {{1}} : Prenom

```text
Bonjour {{1}},

J'aimerais comprendre quelque chose.

Qu'est-ce qui t'empeche aujourd'hui de passer a l'action : le budget, le temps, la peur de te tromper, ou autre chose ?

Reponds-moi franchement.
```

## post_closer_call

- Type : Nouveau message
- Timing : Derniere relance
- Audience : Contacts encore chauds

Variables :
- {{1}} : Prenom
- {{2}} : Lien de reservation closer

```text
Bonjour {{1}},

Si tu veux qu'on regarde ta situation plus serieusement, tu peux reserver un echange ici :
{{2}}

Tu pourras poser tes questions et voir si l'accompagnement est vraiment fait pour toi.
```
