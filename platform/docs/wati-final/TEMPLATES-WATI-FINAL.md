# Templates Wati Finalises

> Statut au 20/05/2026 :
> ce lot ne doit plus etre soumis en l'etat.
> Le client a demande de conserver la base redactionnelle du document v2,
> puis d'ajouter seulement les nouveaux rappels et messages manquants.
> La source client de reference est maintenant :
> [messages-challenge-amazon-fba-v2.1-validation-client.docx](</C:/Users/tobid/Downloads/WHATSAPP SYSTEME IO/platform/docs/messages-v2.1/messages-challenge-amazon-fba-v2.1-validation-client.docx>)
> et son support markdown :
> [messages-challenge-amazon-fba-v2.1-validation-client.md](</C:/Users/tobid/Downloads/WHATSAPP SYSTEME IO/platform/docs/messages-v2.1/messages-challenge-amazon-fba-v2.1-validation-client.md>)

> Les templates ci-dessous restent un lot de travail intermediaire,
> mais ne constituent plus la base de validation client.

## Positionnement

Cette version est ecrite comme si **le formateur lui-meme** ecrivait directement au prospect.

Le ton retenu est :

- humain
- direct
- simple
- sobre
- jamais trop markete
- jamais trop parfait

L'objectif n'est pas de "faire automatisation". L'objectif est de faire **conversation credible**.

## Contraintes retenues

- categorie Wati : `MARKETING`
- sous-categorie : `STANDARD`
- langue : `fr`
- placeholders du systeme : `{{1}}`, `{{2}}`, `{{3}}`
- messages volontairement courts pour faciliter l'approbation Meta/Wati
- pas de placeholders editoriaux flous du type `[NOMBRE]`, `[DUREE]`, `[POINT CLE]`

## Mapping des variables

| Variable | Usage |
|---|---|
| `{{1}}` | Prenom du contact |
| `{{2}}` | Heure du live sur `countdown_j1` |
| `{{2}}` | Lien StreamYard sur `live_day1`, `live_day2_*`, `live_day3_*` |
| `{{2}}` | Lien OnceHub sur `post_recap_*` et `post_followup` |
| `{{2}}` | Lien de paiement sur `live_day3_offer` |
| `{{3}}` | Heure de la session sur les templates `live_day*` |

## Templates

### `welcome`

Variables:
- `{{1}}` = prenom

Texte:

```text
Bonjour {{1}},

Ravi de t'avoir avec moi pour le Challenge Amazon FBA.

Pour que je t'oriente correctement, reponds juste avec un chiffre :
1 = je pars de zero
2 = j'ai deja commence a vendre en ligne
3 = j'ai surtout une question sur le challenge
```

### `countdown_j6`

Variables:
- `{{1}}` = prenom

Texte:

```text
Bonjour {{1}},

Je te pose une question simple avant qu'on demarre :

Aujourd'hui, ton plus gros frein pour te lancer sur Amazon FBA, c'est quoi ?

Le temps, le budget, le choix du produit, ou autre chose ? Reponds-moi ici.
```

### `countdown_j5`

Variables:
- `{{1}}` = prenom

Texte:

```text
{{1}}, petit point avant la suite.

Beaucoup de vendeurs Amazon ne touchent jamais leurs produits. Amazon stocke, expédie et gere une grosse partie de l'operation.

C'est justement ce qu'on va remettre a plat ensemble.

De ton cote, qu'est-ce qui t'intrigue le plus dans ce modele ?
```

### `countdown_j4`

Variables:
- `{{1}}` = prenom

Texte:

```text
Bonjour {{1}},

On a un tres bon groupe pour cette edition, avec des profils tres differents.

Certains partent de zero, d'autres ont deja essaye de vendre en ligne, mais tous viennent avec la meme envie : comprendre comment lancer quelque chose de serieux.

Tu verras, on va avancer simplement et concretement.
```

### `countdown_j3`

Variables:
- `{{1}}` = prenom

Texte:

```text
{{1}}, on entre dans le dur.

Sur les 3 sessions, je vais te montrer comment Amazon FBA fonctionne concretement, comment choisir quoi vendre, et comment poser une base propre pour lancer.

Mon objectif, c'est que tu repartes avec une vision claire, pas avec plus de confusion.

Le sujet qui t'interesse le plus aujourd'hui, c'est lequel ?
```

### `countdown_j2`

Variables:
- `{{1}}` = prenom

Texte:

```text
Bonjour {{1}},

Dans 2 jours, on commence.

Quelques points simples :
- le live se fait sur StreamYard
- tu recevras ton lien ici avant chaque session
- pas besoin de creer de compte
- si tu arrives 5 minutes en avance, c'est parfait

Si tu as une question pratique avant le debut, reponds-moi ici.
```

### `countdown_j1`

Variables:
- `{{1}}` = prenom
- `{{2}}` = heure du Jour 1

Texte:

```text
{{1}}, on demarre demain a {{2}}.

Je t'enverrai le lien ici avant le live.

Prends juste le creneau au calme si tu peux, parce que la premiere session pose toute la base pour la suite.

A demain.
```

### `live_day1`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien StreamYard Jour 1
- `{{3}}` = heure Jour 1

Texte:

```text
Bonjour {{1}},

On demarre aujourd'hui.

Le live commence a {{3}}.
Voici ton lien pour nous rejoindre : {{2}}

Connecte-toi quelques minutes avant si tu peux. A tout a l'heure.
```

### `live_day2_attended`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien StreamYard Jour 2
- `{{3}}` = heure Jour 2

Texte:

```text
Bonjour {{1}},

Merci pour ta presence hier.

On continue aujourd'hui a {{3}}.
Voici ton lien pour la session du jour : {{2}}

On va aller plus loin que ce qu'on a vu hier.
```

### `live_day2_registered_absent`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien StreamYard Jour 2
- `{{3}}` = heure Jour 2

Texte:

```text
Bonjour {{1}},

Je n'ai pas vu ton passage hier.

Pas grave, mais ne rate pas la suite.
On reprend aujourd'hui a {{3}} et voici ton lien : {{2}}

Dis-moi juste : qu'est-ce qui t'a empeche d'etre la hier ?
```

### `live_day2_not_registered`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien StreamYard Jour 2
- `{{3}}` = heure Jour 2

Texte:

```text
Bonjour {{1}},

Le premier live est passe, mais tu peux encore prendre le train en marche.

La prochaine session est aujourd'hui a {{3}}.
Voici le lien : {{2}}

Si tu peux etre la, tu vas deja recuperer l'essentiel pour repartir proprement.
```

### `live_day3_attended`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien StreamYard Jour 3
- `{{3}}` = heure Jour 3

Texte:

```text
Bonjour {{1}},

Merci d'avoir ete la hier.

On se retrouve aujourd'hui a {{3}} pour la derniere session.
Voici ton lien : {{2}}

Je vais te montrer comment assembler tout ca de maniere concrete.
```

### `live_day3_registered_absent`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien StreamYard Jour 3
- `{{3}}` = heure Jour 3

Texte:

```text
Bonjour {{1}},

Je t'ecris avant la derniere session.
Tu t'etais inscrit hier, mais je ne t'ai pas vu passer.

Aujourd'hui, on se retrouve a {{3}} et voici ton lien : {{2}}

Si tu peux, essaie vraiment d'etre la. Et si quelque chose t'a bloque hier, dis-moi.
```

### `live_day3_not_registered`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien StreamYard Jour 3
- `{{3}}` = heure Jour 3

Texte:

```text
Bonjour {{1}},

On arrive a la derniere session du challenge.
Elle a lieu aujourd'hui a {{3}}.
Voici le lien pour nous rejoindre : {{2}}

Meme si tu n'as pas suivi le debut, ca vaut le coup d'etre la pour voir la logique d'ensemble.
```

### `post_recap_attended`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien OnceHub

Texte:

```text
Bonjour {{1}},

Merci pour ta presence hier.

Si tu veux aller plus loin et qu'on regarde ta situation plus serieusement, tu peux reserver ici : {{2}}

Si tu preferes, tu peux aussi me repondre directement et me dire ou tu en es.
```

### `post_recap_registered_absent`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien OnceHub

Texte:

```text
Bonjour {{1}},

Tu t'etais inscrit pour la session d'hier, mais je ne t'ai pas vu.

Si tu veux quand meme qu'on regarde ta situation et la suite possible pour toi, tu peux reserver ici : {{2}}

Et si tu veux, dis-moi simplement ce qui t'a bloque.
```

### `post_recap_not_registered`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien OnceHub

Texte:

```text
Bonjour {{1}},

Le challenge est termine, mais la suite reste ouverte si tu veux te faire accompagner proprement.

Si tu veux qu'on regarde ton cas et qu'on voie si c'est le bon moment pour toi, tu peux reserver ici : {{2}}

Tu peux aussi me repondre directement si tu as une question simple.
```

### `post_followup`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien OnceHub

Texte:

```text
Bonjour {{1}},

Je te fais un dernier message pour ne pas te laisser repartir avec des zones floues.

Si tu veux qu'on echange serieusement sur ton projet et la suite possible, tu peux reserver ici : {{2}}

Et si ce n'est pas le bon moment, aucun souci, dis-le-moi simplement.
```

### `live_day3_offer`

Variables:
- `{{1}}` = prenom
- `{{2}}` = lien de paiement

Texte:

```text
Bonjour {{1}},

Je t'envoie le lien dont j'ai parle pendant le live : {{2}}

Si tu sens que c'est le bon moment pour te faire accompagner, prends-le tranquillement.

Et si tu veux me poser une vraie question avant de decider, reponds-moi ici.
```

## Note de soumission Wati

- Les messages sont deja au bon format placeholder pour le code actuel.
- Les valeurs d'exemple sont disponibles dans `templates_wati_final.json`.
- Les templates peuvent etre soumis via l'API Wati `POST /api/v1/whatsapp/templates`.
- Si un template existe deja avec le meme nom, il faut verifier son statut avant de le supprimer ou de le recreer.
