# Challenge Amazon FBA

> Obsolete pour validation client.
> Le client a demande de repartir de la base v2 conservee,
> avec ajouts cibles seulement.
> Le document de reference a utiliser desormais est :
> `platform/docs/messages-v2.1/messages-challenge-amazon-fba-v2.1-validation-client.docx`

## Séquence de messages WhatsApp - Version 3

## Document de validation client

### Ce que cette version change

- Cette version V3 intègre les derniers retours du client sur la cadence des rappels, les formulations à corriger et les messages de fin de séquence.
- Le ton retenu reste celui du formateur qui écrit directement : humain, simple, direct et jamais trop marketé.
- Les formulations trop marquées par le genre ont été retirées au profit de formulations neutres comme 'ta présence' ou 'je ne t'ai pas vu'.
- Ce document sert uniquement à valider les messages avant soumission finale dans Wati.

### Structure retenue

- Pré-challenge : 7 messages de préparation
- Jour 1 : 3 messages (2h avant, 10 min avant, 5 min après)
- Jour 2 : 5 messages (3 branches à 2h + 10 min avant + 5 min après)
- Jour 3 : 6 messages (3 branches à 2h + 10 min avant + 5 min après + lien de paiement)
- Post-challenge : 6 messages (replays, témoignages, frein, prise de rendez-vous)

## Pré-challenge

### Message 1/27 - Bienvenue

- Clé Wati : welcome
- Moment d'envoi : Immédiatement après l'inscription
- Public concerné : Tous les inscrits

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)

```text
Bonjour {{1}},

Je suis ravi de t'accueillir pour le Challenge Amazon FBA.

Pendant les prochains jours, je vais t'envoyer ici l'essentiel pour te préparer aux 3 directs.

Dis-moi : as-tu déjà entendu parler de la vente sur Amazon ?
```

### Message 2/27 - Question sur la situation actuelle

- Clé Wati : countdown_j6
- Moment d'envoi : J-6
- Public concerné : Tous les inscrits

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)

```text
Bonjour {{1}},

Avant qu'on démarre, j'ai une question simple pour toi.

Aujourd'hui, ton plus gros frein pour te lancer sur Amazon FBA, c'est quoi ?

Le temps, le budget, le choix du produit, ou autre chose ? Réponds-moi ici.
```

### Message 3/27 - Curiosité

- Clé Wati : countdown_j5
- Moment d'envoi : J-5
- Public concerné : Tous les inscrits

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)

```text
Bonjour {{1}},

Petit point avant la suite.

Beaucoup de vendeurs Amazon ne touchent jamais leurs produits. Amazon stocke, expédie et gère une grosse partie de l'opération.

C'est justement ce qu'on va remettre à plat ensemble.

De ton côté, qu'est-ce qui t'intrigue le plus dans ce modèle ?
```

### Message 4/27 - Communauté et engagement

- Clé Wati : countdown_j4
- Moment d'envoi : J-4
- Public concerné : Tous les inscrits

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)

```text
Bonjour {{1}},

On a déjà un très bon groupe pour cette édition, avec des profils très différents.

Certains partent de zéro, d'autres ont déjà essayé de vendre en ligne, mais tous viennent avec la même envie : comprendre comment lancer quelque chose de sérieux.

Tu verras, on va avancer simplement et concrètement.
```

### Message 5/27 - Programme des 3 directs

- Clé Wati : countdown_j3
- Moment d'envoi : J-3
- Public concerné : Tous les inscrits

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)

```text
Bonjour {{1}},

Voici ce qu'on va voir ensemble pendant les 3 directs :

1. La méthode FBA de A à Z
2. Construire Ton Business Amazon Pas à Pas
3. Le Secret des Vendeurs à Succès sur Amazon

Pense à t'inscrire en avance s'il te plaît.

Seras-tu parmi nous en direct ?
```

### Message 6/27 - Informations pratiques

- Clé Wati : countdown_j2
- Moment d'envoi : J-2
- Public concerné : Tous les inscrits

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)

```text
Bonjour {{1}},

Dans 2 jours, on commence.

Quelques points simples :
- le live se fait sur StreamYard
- tu recevras ton lien ici avant chaque session
- pas besoin de créer de compte
- si tu arrives 5 minutes en avance, c'est parfait

Si tu as une question pratique avant le début, réponds-moi ici.
```

### Message 7/27 - La veille du premier live

- Clé Wati : countdown_j1
- Moment d'envoi : J-1
- Public concerné : Tous les inscrits

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Heure de la session du Jour 1 (exemple : 21h00)

```text
Bonjour {{1}},

On démarre demain à {{2}}.

Je t'enverrai le lien ici avant le live.

Prends juste le créneau au calme si tu peux, parce que la première session pose toute la base pour la suite.

À demain.
```

## Jour 1

### Message 8/27 - Jour 1 - rappel principal

- Clé Wati : live_day1_h2
- Moment d'envoi : 2 heures avant le live
- Public concerné : Tous les inscrits actifs

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 1 (exemple : https://streamyard.com/watch/exemple-j1)
- {{3}} : Heure du live Jour 1 (exemple : 21h00)

```text
Bonjour {{1}},

On se retrouve ce soir à {{3}} pour : La méthode FBA de A à Z

Voici ton lien pour nous rejoindre :
{{2}}

Essaie d'être là dès le début, cette première session pose toute la base.
```

### Message 9/27 - Jour 1 - rappel 10 minutes avant

- Clé Wati : live_day1_h10
- Moment d'envoi : 10 minutes avant le live
- Public concerné : Tous les inscrits actifs

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 1 (exemple : https://streamyard.com/watch/exemple-j1)

```text
Bonjour {{1}},

On démarre dans 10 minutes.

Voici ton lien :
{{2}}

À tout de suite.
```

### Message 10/27 - Jour 1 - relance 5 minutes après le début

- Clé Wati : live_day1_hplus5
- Moment d'envoi : 5 minutes après le début du live
- Public concerné : Ceux qui n'ont pas cliqué ou ouvert le message précédent

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 1 (exemple : https://streamyard.com/watch/exemple-j1)

```text
Bonjour {{1}},

On a commencé il y a 5 minutes.

Si tu comptais nous rejoindre, tu peux encore entrer maintenant :
{{2}}
```

## Jour 2

### Message 11/27 - Jour 2 - 2h avant pour les présents du Jour 1

- Clé Wati : live_day2_attended_h2
- Moment d'envoi : 2 heures avant le live
- Public concerné : Présents au Jour 1

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 2 (exemple : https://streamyard.com/watch/exemple-j2)
- {{3}} : Heure du live Jour 2 (exemple : 21h00)

```text
Bonjour {{1}},

Merci pour ta présence hier.

Ce soir à {{3}}, on continue avec : Construire Ton Business Amazon Pas à Pas

Ton lien :
{{2}}

Hier, quel point t'a le plus marqué ?
```

### Message 12/27 - Jour 2 - 2h avant pour les inscrits absents au Jour 1

- Clé Wati : live_day2_registered_absent_h2
- Moment d'envoi : 2 heures avant le live
- Public concerné : Inscrits StreamYard Jour 1 mais absents

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 2 (exemple : https://streamyard.com/watch/exemple-j2)
- {{3}} : Heure du live Jour 2 (exemple : 21h00)

```text
Bonjour {{1}},

Je ne t'ai pas vu hier soir.

Ce soir à {{3}}, on continue avec : Construire Ton Business Amazon Pas à Pas

Voici ton lien :
{{2}}

Dis-moi simplement ce qui t'a empêché d'être là hier.
```

### Message 13/27 - Jour 2 - 2h avant pour les non inscrits au Jour 1

- Clé Wati : live_day2_not_registered_h2
- Moment d'envoi : 2 heures avant le live
- Public concerné : Aucune interaction StreamYard Jour 1

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 2 (exemple : https://streamyard.com/watch/exemple-j2)
- {{3}} : Heure du live Jour 2 (exemple : 21h00)

```text
Bonjour {{1}},

Si tu n'as pas pu suivre le premier direct, tu peux encore prendre le train en marche.

Ce soir à {{3}} : Construire Ton Business Amazon Pas à Pas

Voici le lien :
{{2}}
```

### Message 14/27 - Jour 2 - rappel 10 minutes avant

- Clé Wati : live_day2_h10
- Moment d'envoi : 10 minutes avant le live
- Public concerné : Tous les contacts ciblés pour Jour 2

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 2 (exemple : https://streamyard.com/watch/exemple-j2)

```text
Bonjour {{1}},

On démarre dans 10 minutes.

Voici ton lien :
{{2}}

À tout de suite.
```

### Message 15/27 - Jour 2 - relance 5 minutes après le début

- Clé Wati : live_day2_hplus5
- Moment d'envoi : 5 minutes après le début du live
- Public concerné : Ceux qui n'ont pas cliqué ou ouvert le message précédent

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 2 (exemple : https://streamyard.com/watch/exemple-j2)

```text
Bonjour {{1}},

On a commencé il y a 5 minutes.

Si tu voulais nous rejoindre, tu peux encore entrer maintenant :
{{2}}
```

## Jour 3

### Message 16/27 - Jour 3 - 2h avant pour les présents du Jour 2

- Clé Wati : live_day3_attended_h2
- Moment d'envoi : 2 heures avant le live
- Public concerné : Présents au Jour 2

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 3 (exemple : https://streamyard.com/watch/exemple-j3)
- {{3}} : Heure du live Jour 3 (exemple : 21h00)

```text
Bonjour {{1}},

Merci pour ta présence hier.

Ce soir à {{3}} : Le Secret des Vendeurs à Succès sur Amazon

Ton lien :
{{2}}

Hier, quelle idée t'a le plus parlé ?
```

### Message 17/27 - Jour 3 - 2h avant pour les inscrits absents au Jour 2

- Clé Wati : live_day3_registered_absent_h2
- Moment d'envoi : 2 heures avant le live
- Public concerné : Inscrits StreamYard Jour 2 mais absents

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 3 (exemple : https://streamyard.com/watch/exemple-j3)
- {{3}} : Heure du live Jour 3 (exemple : 21h00)

```text
Bonjour {{1}},

Je ne t'ai pas vu hier.

Ce soir à {{3}} : Le Secret des Vendeurs à Succès sur Amazon

Ton lien :
{{2}}

Essaie vraiment d'être là, c'est la session la plus importante.
```

### Message 18/27 - Jour 3 - 2h avant pour les non inscrits aux jours précédents

- Clé Wati : live_day3_not_registered_h2
- Moment d'envoi : 2 heures avant le live
- Public concerné : Aucune interaction StreamYard Jour 1 ou Jour 2

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 3 (exemple : https://streamyard.com/watch/exemple-j3)
- {{3}} : Heure du live Jour 3 (exemple : 21h00)

```text
Bonjour {{1}},

Même si tu n'as pas encore suivi les directs, tu peux encore nous rejoindre ce soir.

Dernière session à {{3}} : Le Secret des Vendeurs à Succès sur Amazon

Voici le lien :
{{2}}
```

### Message 19/27 - Jour 3 - rappel 10 minutes avant

- Clé Wati : live_day3_h10
- Moment d'envoi : 10 minutes avant le live
- Public concerné : Tous les contacts ciblés pour Jour 3

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 3 (exemple : https://streamyard.com/watch/exemple-j3)

```text
Bonjour {{1}},

On démarre dans 10 minutes.

Voici ton lien :
{{2}}

À tout de suite.
```

### Message 20/27 - Jour 3 - relance 5 minutes après le début

- Clé Wati : live_day3_hplus5
- Moment d'envoi : 5 minutes après le début du live
- Public concerné : Ceux qui n'ont pas cliqué ou ouvert le message précédent

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien StreamYard Jour 3 (exemple : https://streamyard.com/watch/exemple-j3)

```text
Bonjour {{1}},

On a commencé il y a 5 minutes.

Si tu comptais nous rejoindre, tu peux encore entrer maintenant :
{{2}}
```

### Message 21/27 - Jour 3 - lien de paiement 2 heures après le début

- Clé Wati : live_day3_offer_hplus2
- Moment d'envoi : 2 heures après le début du live
- Public concerné : Inscrits StreamYard Jour 3 n'ayant pas encore acheté

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien de paiement ou de programme (exemple : https://paiement.exemple.com/programme)

```text
Bonjour {{1}},

Comme promis, voici le lien dont j'ai parlé pendant le direct :
{{2}}

Prends-le tranquillement.

Et si tu veux poser une vraie question avant de décider, réponds-moi ici.
```

Point(s) à valider :
- Ce message doit être coupé automatiquement pour les contacts qui ont déjà payé dans la journée.

## Post-challenge

### Message 22/27 - J+1 - replay pour les plus engagés

- Clé Wati : post_replay_attended
- Moment d'envoi : J+1
- Public concerné : Présents à la session 3

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Replay Jour 1 (exemple : https://replay.exemple.com/j1)
- {{3}} : Replay Jour 2 (exemple : https://replay.exemple.com/j2)
- {{4}} : Replay Jour 3 (exemple : https://replay.exemple.com/j3)

```text
Bonjour {{1}},

Merci encore pour ta présence pendant ce challenge.

Comme promis, voici les replays :
Jour 1 : {{2}}
Jour 2 : {{3}}
Jour 3 : {{4}}

Prends le temps de revoir les points clés.
```

Point(s) à valider :
- À remplacer par les vrais liens replay transmis par le client.

### Message 23/27 - J+1 - replay pour rattrapage

- Clé Wati : post_replay_partial
- Moment d'envoi : J+1
- Public concerné : Présents partiels ou absents partiels

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Replay Jour 1 (exemple : https://replay.exemple.com/j1)
- {{3}} : Replay Jour 2 (exemple : https://replay.exemple.com/j2)
- {{4}} : Replay Jour 3 (exemple : https://replay.exemple.com/j3)

```text
Bonjour {{1}},

Comme promis, voici les replays pour rattraper ce que tu as manqué :
Jour 1 : {{2}}
Jour 2 : {{3}}
Jour 3 : {{4}}

Regarde-les à ton rythme, puis dis-moi quel point t'a le plus aidé.
```

Point(s) à valider :
- À remplacer par les vrais liens replay transmis par le client.

### Message 24/27 - J+1 - replay pour les absents

- Clé Wati : post_replay_absent
- Moment d'envoi : J+1
- Public concerné : Aucun live suivi

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Replay Jour 1 (exemple : https://replay.exemple.com/j1)
- {{3}} : Replay Jour 2 (exemple : https://replay.exemple.com/j2)
- {{4}} : Replay Jour 3 (exemple : https://replay.exemple.com/j3)

```text
Bonjour {{1}},

Tu n'as pas pu suivre les directs, donc je te laisse quand même les replays ici :
Jour 1 : {{2}}
Jour 2 : {{3}}
Jour 3 : {{4}}

Regarde-les à ton rythme, puis dis-moi si tu veux qu'on fasse le point.
```

Point(s) à valider :
- Ce message remplace la logique vague du 'réponds INFO'.
- À remplacer par les vrais liens replay transmis par le client.

### Message 25/27 - Partage de témoignages

- Clé Wati : post_testimonials
- Moment d'envoi : J+2 ou J+3
- Public concerné : Contacts encore actifs

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)

```text
Bonjour {{1}},

Je te partage deux retours de personnes qui sont passées à l'action après le challenge :

[TÉMOIGNAGE 1 COURT]

[TÉMOIGNAGE 2 COURT]

Si tu veux qu'on voie si c'est possible pour toi aussi, réponds-moi simplement ici.
```

Point(s) à valider :
- À remplacer par 2 témoignages courts validés par le client.

### Message 26/27 - Comprendre le frein réel

- Clé Wati : post_inaction_reason
- Moment d'envoi : J+3 ou J+4
- Public concerné : Contacts qui n'ont pas encore avancé

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)

```text
Bonjour {{1}},

J'aimerais comprendre quelque chose.

Qu'est-ce qui t'empêche aujourd'hui de passer à l'action : le budget, le temps, la peur de te tromper, ou autre chose ?

Réponds-moi franchement.
```

### Message 27/27 - Prise de rendez-vous closer

- Clé Wati : post_closer_call
- Moment d'envoi : Dernière relance
- Public concerné : Contacts encore chauds

Variables :
- {{1}} : Prénom du contact (exemple : Sonia)
- {{2}} : Lien formulaire closer / OnceHub (exemple : https://www.ecommercecentrale.com/formulaire-challenge)

```text
Bonjour {{1}},

Si tu veux qu'on regarde ta situation plus sérieusement, tu peux réserver un échange ici :
{{2}}

Tu pourras poser tes questions et voir si l'accompagnement est vraiment fait pour toi.
```
