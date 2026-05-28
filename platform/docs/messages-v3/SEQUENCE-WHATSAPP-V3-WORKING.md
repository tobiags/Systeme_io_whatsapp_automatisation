# Sequence WhatsApp V3 — Base de travail

## Objet

Ce document remplace la logique de simple "correction de wording" de la V2.

Le retour client du 19 mai 2026 montre que nous ne sommes plus sur une retouche cosmetique.  
Nous sommes sur une **refonte de la sequence**, avec :

- nouveaux timings
- nouveaux rappels
- nouveaux messages de fin
- nouvelles conditions d'arret
- nouveaux contenus a integrer

Conclusion immediate :

- **arreter la soumission du lot Wati actuel**
- **reprendre la matrice des messages avant toute nouvelle soumission**

## Corrections textuelles deja confirmees

### 1. Ton

Le ton valide reste :

- humain
- direct
- simple
- conversationnel
- comme si le formateur ecrivait lui-meme

### 2. Formulations a corriger partout

Le client a explicitement demande d'eviter les formulations qui marquent le genre.

Donc on retire ou corrige les formulations du type :

- "tu es present(e)"
- "tu t'es inscrit(e)"
- "tu n'as pas pu etre la" quand la phrase sonne trop diffusee

On privilegie :

- "merci pour ta presence"
- "je ne t'ai pas vu au live"
- "ton nom est bien inscrit"
- "ta place etait bien reservee"

### 3. Vrais titres des directs StreamYard

Les titres a retenir dans la V3 sont :

1. **La methode FBA de A a Z**
2. **Construire Ton Business Amazon Pas a Pas**
3. **Le Secret des Vendeurs a Succes sur Amazon**

Ils doivent remplacer les anciens placeholders et anciens intitulés partout dans la source editoriale.

## Ce que le retour client change reellement

## 1. Jour 1

Le client veut :

- un message principal avant le live
- un rappel **10 min avant**
- un rappel **5 min apres le debut du live**
- ce rappel +5 min doit viser **ceux qui n'ont pas clique ou ouvert le message precedent**

Impact :

- le systeme actuel a deja des taches planifiees
- mais les timings actuels ne correspondent pas a cette demande
- et le ciblage "n'a pas ouvert / n'a pas clique" n'est pas encore en place

## 2. Jour 2

Le client veut :

- un message **2h avant**
- un rappel **10 min avant**
- un rappel **5 min apres le debut**
- une question contextuelle pour ceux qui ont participe au live du jour precedent

Impact :

- la logique de branchement par comportement existe deja
- mais elle doit etre combinee avec une logique de rappels multi-timings
- cela augmente fortement le nombre de templates si on garde une personnalisation par branche

## 3. Jour 3

Le client veut :

- un message **2h avant**
- un rappel **10 min avant**
- un rappel **5 min apres le debut**
- une question contextuelle pour ceux qui etaient presents au Jour 2
- le CTA paiement **2h apres le debut du live**

Impact :

- le trigger H+2 existe deja pour `live_day3_offer`
- mais la sequence avant le live doit etre revue
- le wording doit etre refait en cohérence avec la V3

## 4. Arret des messages apres achat

Le client demande de stopper le broadcasting a ceux qui ont pris la formation le jour meme.

Impact :

- le code gere deja le score `paid_offer`
- mais **il n'existe pas aujourd'hui de gate explicite dans le moteur de broadcast pour sortir automatiquement les acheteurs de la sequence**

Il faut donc ajouter une regle du type :

- si `ScoreEvent.event_type == paid_offer`
- alors exclure le contact des broadcasts et rappels restants

## 5. J+1 et "INFO"

Le client a raison sur un point critique :

> si le message demande de repondre "INFO", il faut savoir ce qui se passe ensuite

Aujourd'hui :

- ce comportement n'est pas formellement specifie dans le produit
- il n'existe pas de flux clair "INFO -> replay"

La meilleure correction produit est :

- **ne pas garder un CTA flou de type "reponds INFO"**
- envoyer directement un vrai message J+1 avec les replays, une fois les liens recus

## 6. Fin de sequence

Le client demande explicitement des messages supplementaires pour :

- partager les temoignages de ceux qui ont reussi
- comprendre pourquoi certains ne sont pas passes a l'action
- pousser vers la reservation d'un call closer

Conclusion :

- la fin de sequence actuelle est insuffisante
- la V3 doit inclure une vraie **phase de conversion post-challenge**

## Lecture de l'etat actuel du systeme

## Ce qui existe deja

### Scheduler / taches planifiees

Le code actuel de [scheduler.py](/C:/Users/tobid/Downloads/WHATSAPP%20SYSTEME%20IO/platform/services/campaigns/app/scheduler.py) et [tasks.py](/C:/Users/tobid/Downloads/WHATSAPP%20SYSTEME%20IO/platform/services/campaigns/app/tasks.py) couvre deja :

- `H-6`
- `H-45`
- `H-10`
- `H+30 recap`
- `H+2 day3 offer`

### Branching comportemental

Le code actuel de [rules.py](/C:/Users/tobid/Downloads/WHATSAPP%20SYSTEME%20IO/platform/services/campaigns/app/rules.py) et [main.py](/C:/Users/tobid/Downloads/WHATSAPP%20SYSTEME%20IO/platform/services/campaigns/app/main.py) gere deja :

- presents live
- inscrits StreamYard mais absents
- non inscrits

### H+2 Jour 3

Le trigger manuel/planifie pour `live_day3_offer` existe deja.

## Ce qui n'existe pas encore

### 1. Filtre "non ouvreurs / non cliqueurs"

Ce ciblage n'est pas encore implemente comme regle claire de rappel +5 min.

### 2. Arret automatique apres `paid_offer`

Le score existe, la sortie de sequence automatique n'existe pas encore comme regle de diffusion.

### 3. Flux "replay"

La V2 mentionnait parfois un CTA "INFO", mais le comportement applicatif n'est pas formalise.

### 4. Phase de fin enrichie

La sequence actuelle ne couvre pas encore correctement :

- temoignages
- relance inaction
- prise de rendez-vous closer

## Proposition de matrice V3

## Phase 1 — Pre-challenge

On conserve les 7 messages de countdown, mais on corrige :

- les formulations neutres
- les vrais titres de lives
- les formulations trop broadcast

## Phase 2 — Jour 1

Templates a prevoir :

1. `live_day1_h2`
2. `live_day1_h10`
3. `live_day1_hplus5_unopened_unclicked`

## Phase 3 — Jour 2

### Branche presents Jour 1

1. `live_day2_attended_h2`
2. `live_day2_attended_h10`
3. `live_day2_attended_hplus5_unopened_unclicked`

### Branche inscrits absents Jour 1

4. `live_day2_registered_absent_h2`
5. `live_day2_registered_absent_h10`
6. `live_day2_registered_absent_hplus5_unopened_unclicked`

### Branche non inscrits Jour 1

7. `live_day2_not_registered_h2`
8. `live_day2_not_registered_h10`
9. `live_day2_not_registered_hplus5_unopened_unclicked`

## Phase 4 — Jour 3

### Branche presents Jour 2

1. `live_day3_attended_h2`
2. `live_day3_attended_h10`
3. `live_day3_attended_hplus5_unopened_unclicked`

### Branche inscrits absents Jour 2

4. `live_day3_registered_absent_h2`
5. `live_day3_registered_absent_h10`
6. `live_day3_registered_absent_hplus5_unopened_unclicked`

### Branche non inscrits Jour 2

7. `live_day3_not_registered_h2`
8. `live_day3_not_registered_h10`
9. `live_day3_not_registered_hplus5_unopened_unclicked`

### Offre

10. `live_day3_offer_hplus2`

## Phase 5 — Post-challenge

Templates a prevoir :

1. `post_replay_attended`
2. `post_replay_partial`
3. `post_replay_absent`
4. `post_testimonials`
5. `post_inaction_reason`
6. `post_closer_call`

## Observation importante sur Wati

Si on suit strictement cette logique, le nombre de templates augmente fortement.

Ce n'est pas un detail editorial.  
C'est une decision produit.

Deux approches sont possibles :

### Approche A — hyper specifique

Un template par timing et par branche.

Avantage :

- messages tres cibles

Inconvenient :

- beaucoup plus de templates a soumettre
- maintenance plus lourde

### Approche B — semi mutualisee

Mutualiser certains rappels generiques :

- un rappel H-10 generique par jour
- un rappel H+5 generique par jour

et garder les branches uniquement pour les messages H-2 plus contextuels.

Avantage :

- moins de templates
- soumission Wati plus legere

Inconvenient :

- moins de personnalisation sur les rappels courts

## Recommendation actuelle

Pour limiter l'explosion du nombre de templates Wati, la meilleure base V3 est :

- **messages H-2 differencies par branche**
- **messages H-10 mutualises par jour**
- **messages H+5 mutualises par jour et filtres par comportement**
- **phase post-challenge enrichie**

## Inputs encore manquants

Avant de produire un document client final complet, il manque encore :

1. les **3 liens replay**
2. les **temoignages exacts** a pousser
3. confirmation du **lien de paiement final** si celui en prod n'est pas encore verrouille

## Decision de travail

Avant de regenerer le Word client final :

1. mettre a jour la source editoriale V3
2. corriger la matrice fonctionnelle dans la doc de travail
3. redecouper les templates Wati selon la vraie logique V3
4. seulement ensuite produire le nouveau `.docx`

## Statut

Ce document est la **base de reprise V3**.

Il sert a :

- interrompre proprement la soumission Wati de la V2
- recadrer la logique produit
- preparer le prochain document Word client sur une base saine
