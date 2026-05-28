# Cadrage fonctionnel - Challenge Amazon FBA

**Date :** 2026-04-25  
**Objet :** definir le fonctionnement metier concret du `Challenge Amazon FBA` pour alimenter la plateforme WhatsApp, les sequences de messages, les regles de segmentation, le dashboard et les modules LLM.  
**Perimetre :** ce document traite uniquement du challenge lui-meme, de son deroule, de ses cohortes, de ses messages, de ses evenements, des FAQ, des objections et des regles de segmentation specifiques.

---

## 1. Vue d'ensemble du challenge

Le programme s'appelle officiellement `Challenge Amazon FBA`.

Il s'agit d'un challenge gratuit organise `2 fois par mois`, sur `3 jours`, du `jeudi au samedi`.

Le challenge s'adresse principalement a des profils `debutants`, avec une promesse d'accompagnement, de clarification et de progression autour d'Amazon FBA.

Le systeme doit donc etre pense pour :

- rassurer des inscrits peu avances
- les aider a comprendre le deroule concret
- les pousser a assister effectivement aux lives
- gerer les differences de fuseaux horaires
- traiter les questions repetitives sans friction
- detecter rapidement les freins financiers et les besoins d'accompagnement humain

---

## 2. Structure fonctionnelle des cohortes

Le challenge doit etre gere selon `2 cohortes distinctes`.

### 2.1 Cohorte EU

- cible : Europe
- horaire live : `21h00 Europe`
- langue et ton : francais simple, pedagogique, rassurant
- besoin principal : clarte, guidage, reduction de l'incertitude

### 2.2 Cohorte US-CA

- cible : Montreal / New York / audience nord-americaine equivalente
- horaire live : `19h00 Montreal / New York`
- gestion separee de la cohorte
- meme logique fonctionnelle, mais avec ses propres horaires, rappels et liens de session

### 2.3 Regle de base

Chaque inscrit doit etre rattache des l'entree a :

- une `edition` du challenge
- une `cohorte horaire`
- un `calendrier de relance`
- un `lien de session` associe a son edition et a sa region

Le systeme ne doit jamais supposer qu'un meme lien ou un meme horaire vaut pour tout le monde.

### 2.4 Source reelle des cohortes

Les cohortes existent deja cote `Systeme.io` sous forme de `deux listes separees telechargeables`.

Implications fonctionnelles :

- il n'est pas necessaire d'inferer la cohorte a partir du pays si la liste source est deja fiable
- l'import ou la synchronisation doit conserver la liste d'origine comme verite de rattachement initiale
- la plateforme peut ensuite enrichir ce rattachement avec une edition de challenge et un calendrier de relance

---

## 3. Deroule fonctionnel du challenge sur 3 jours

Le challenge suit une logique en `3 temps` :

- mobilisation avant le demarrage
- engagement pendant les 3 jours
- relance et conversion apres la fin

### 3.1 Phase avant challenge

Objectif :

- confirmer l'inscription
- orienter le participant
- lui faire comprendre quand cela commence
- le preparer a assister au premier live

Moments critiques :

- inscription
- bienvenue
- rappel du jour de debut
- confirmation de la bonne cohorte horaire
- rappel avec lien de connexion au bon moment

### 3.2 Jour 1 - Jeudi

Objectif :

- transformer l'inscrit en participant reel
- obtenir une premiere presence au live
- ancrer la valeur percue

Messages et actions attendus :

- rappel d'ouverture du challenge
- rappel d'horaire selon cohorte
- envoi du lien StreamYard de l'edition
- verification de l'email deja envoye si le participant dit ne rien avoir recu
- relance si non-presence ou non-ouverture
- message post-live de recap ou de rattrapage

### 3.3 Jour 2 - Vendredi

Objectif :

- maintenir la dynamique
- eviter la chute d'attention apres le premier jour
- renforcer l'engagement comportemental

Messages et actions attendus :

- rappel de la session du jour
- message de continute pedagogique
- lien de session du jour si necessaire
- relance des absents du Jour 1
- message specifique pour ceux qui ont deja participe

### 3.4 Jour 3 - Samedi

Objectif :

- maximiser la presence finale
- preparer la suite commerciale ou la conversion
- traiter les objections de derniere minute

Messages et actions attendus :

- rappel final de la derniere session
- message de mise en valeur de ce qui sera manque si absent
- lien de session final
- relance des chauds / tres chauds
- suivi post-session oriente vers l'offre ou l'etape suivante

### 3.5 Apres challenge

Objectif :

- convertir les plus engages
- re-engager ceux qui ont manque une partie du challenge
- distinguer les curieux, les interesses, les objections budgetaires et les cas a reprendre manuellement

Actions attendues :

- message de recap global
- message d'offre ou de suite logique
- messages de reponse aux objections financieres
- priorisation des relances operateur
- sortie de sequence ou reinjection dans une nouvelle edition

---

## 4. Messages a prevoir

Le systeme doit prevoir plusieurs familles de messages.

### 4.1 Messages avant challenge

- message de bienvenue
- message de confirmation d'inscription
- message d'information sur le demarrage
- message de rappel de la cohorte horaire
- message d'acces au groupe WhatsApp
- message de verification si la personne n'a pas recu d'email
- message de rappel que le lien du live sera aussi partage par email et dans les groupes du challenge

### 4.2 Messages Jour 1, Jour 2, Jour 3

- rappel du live du jour
- message avec lien StreamYard
- relance courte avant demarrage
- relance des absents
- message post-live
- message de rattrapage si non-presence
- message de suivi post-pitch pour les objections exprimees en direct

### 4.3 Messages comportementaux

- message pour personne inscrite mais inactive
- message pour personne ayant confirme puis disparu
- message pour personne tres engagee
- message pour personne qui pose des questions frequentes
- message pour personne qui exprime une objection financiere

### 4.4 Messages post-challenge

- recapitulatif
- message d'orientation vers l'offre
- message de reponse aux objections
- relance douce
- relance forte pour profils tres chauds
- proposition de reprise humaine

### 4.5 Contraintes de messaging

Tous les messages doivent pouvoir etre variantes selon :

- `EU` vs `US-CA`
- edition de challenge
- jour du challenge
- statut de presence
- niveau d'engagement
- type de question ou objection

---

## 5. Evenements metier a suivre

Le dashboard, le scoring et l'automatisation doivent suivre au minimum les evenements suivants.

### 5.1 Evenements d'acquisition

- `lead_captured`
- `contact_created`
- `cohort_assigned`
- `challenge_edition_assigned`
- `consent_confirmed`

### 5.2 Evenements de messaging

- `welcome_message_sent`
- `message_delivered`
- `message_opened` si disponible
- `message_clicked` si lien tracke
- `streamyard_link_sent`
- `streamyard_link_clicked`
- `email_live_link_sent`
- `group_live_link_posted`

### 5.3 Evenements de participation

- `day1_live_expected`
- `day1_live_joined`
- `day1_live_missed`
- `day2_live_joined`
- `day2_live_missed`
- `day3_live_joined`
- `day3_live_missed`

### 5.4 Evenements conversationnels

- `question_asked`
- `faq_detected`
- `financial_objection_detected`
- `support_issue_detected`
- `email_not_received_detected`
- `whatsapp_group_request_detected`
- `human_escalation_required`

### 5.5 Evenements commerciaux

- `offer_interest_detected`
- `pricing_question_detected`
- `conversion_intent_detected`
- `payment_started`
- `payment_failed_insufficient_funds`
- `installment_plan_requested`
- `next_challenge_requested`
- `skepticism_detected`
- `payment_completed`
- `followup_manual_queued`

---

## 6. FAQ specifiques au challenge

Les FAQ de base confirmees a traiter en priorite sont :

- `Comment rejoindre le groupe WhatsApp ?`
- `Je me suis inscrit mais je n'ai pas recu d'email.`
- `Quand est-ce que cela commence ?`
- `Combien coute la formation ?`
- `Quand est-ce que vous referez un nouveau challenge ?`

### 6.1 Intentions associees

Ces FAQ doivent etre mappees a des intentions explicites :

- `faq_whatsapp_group_join`
- `faq_email_missing`
- `faq_start_time`
- `faq_offer_price`
- `faq_next_challenge_date`

### 6.2 Reponse attendue du systeme

Le systeme doit :

- donner une reponse claire et courte
- rassurer les debutants
- ne pas noyer la personne dans trop d'informations
- proposer une escalade si la situation ne rentre pas dans la FAQ standard

---

## 7. Objections principales

L'objection dominante confirmee est `financiere`.

### 7.1 Formes possibles de l'objection

- c'est trop cher
- je n'ai pas le budget
- combien cela coute
- je veux reflechir
- je ne suis pas sur de pouvoir investir maintenant
- est-ce qu'il y a une solution plus accessible
- je veux payer plus tard
- je veux payer en plus de fois
- j'ai essaye de payer mais je n'avais pas assez
- je reviendrai plus tard
- c'est interessant mais j'ai peur de perdre mon argent

### 7.2 Traitement attendu

Le systeme doit :

- detecter l'objection sans surreagir
- repondre avec empathie
- rappeler la valeur du challenge et du parcours
- clarifier la distinction entre challenge gratuit et offre payante
- diriger vers un humain si l'objection demande un traitement plus commercial
- distinguer les objections de tresorerie, de timing, de plan de paiement et de scepticisme
- ne pas laisser sans suivi les tentatives de paiement echouees

### 7.3 Intentions associees

- `objection_financial_soft`
- `objection_financial_strong`
- `pricing_information_request`
- `human_sales_followup_needed`
- `installment_plan_request`
- `payment_failure_followup_needed`
- `skeptic_trust_objection`
- `next_challenge_request`

---

## 8. Regles de segmentation specifiques au challenge

La segmentation generale de la plateforme doit etre adaptee au contexte du challenge.

Segments cibles :

- `Froid`
- `Tiede`
- `Chaud`
- `Tres chaud`

### 8.1 Segment Froid

Profil typique :

- inscrit mais peu reactif
- n'ouvre pas les messages
- ne clique pas
- ne rejoint pas le live

Traitement :

- relances simples
- messages rassurants
- clarte maximale
- reduction de la charge cognitive

### 8.2 Segment Tiede

Profil typique :

- lit certains messages
- pose parfois des questions basiques
- s'interesse mais reste passif
- peut manquer le Jour 1 ou le Jour 2

Traitement :

- rappels reguliers
- messages pedagogiques
- mise en avant des benefices concrets du challenge

### 8.3 Segment Chaud

Profil typique :

- confirme sa presence
- clique les liens
- rejoint au moins un live
- pose des questions liees a l'offre ou au fonctionnement

Traitement :

- suivi plus direct
- messages plus actionnables
- relance post-live plus soutenue

### 8.4 Segment Tres chaud

Profil typique :

- participe activement
- pose des questions avancees ou commerciales
- montre une intention d'achat
- revient plusieurs jours de suite

Traitement :

- priorite haute
- relance humaine potentielle
- messages plus personnalises
- suivi conversion

---

## 9. Regles de scoring recommandees pour ce challenge

Le scoring doit refleter les comportements qui comptent vraiment dans le challenge.

### 9.1 Signaux positifs

- inscription validee
- groupe WhatsApp rejoint
- ouverture des messages
- clic sur le lien de live
- presence au Jour 1
- presence au Jour 2
- presence au Jour 3
- question posee
- question sur l'offre
- intention de conversion

### 9.2 Signaux faibles ou neutres

- simple lecture sans action
- question tres basique sans engagement ulterieur

### 9.3 Signaux negatifs ou a surveiller

- absence sur plusieurs jours
- message non delivre ou non consulte
- objection financiere forte repetee
- demande d'aide sans suite
- decrochage apres Jour 1

### 9.4 Regle metier importante

Une objection financiere ne doit pas automatiquement faire chuter fortement le score.

Elle peut au contraire signaler un interet reel si elle apparait chez une personne qui :

- assiste aux lives
- pose des questions sur la formation
- clique les liens
- demande des precisions

Dans ce cas, il faut distinguer :

- `objection financiere = frein`
- `objection financiere = signal d'interet commercial`

---

## 10. Cas de priorisation operateur

Certains profils doivent remonter plus vite dans la file manuelle.

Priorite haute :

- inscrit tres engage avec objection financiere
- personne qui a assiste aux 2 ou 3 jours et demande le prix
- personne qui dit ne pas avoir recu les informations alors qu'elle veut participer
- personne qui demande un accompagnement ou un appel
- personne qui a essaye de payer sans fonds suffisants
- personne qui demande explicitement un plan de paiement
- personne engagee qui demande quand aura lieu le prochain challenge

Priorite moyenne :

- personne tiede avec questions frequentes
- personne ayant clique le lien mais rate le live

Priorite basse :

- personne totalement inactive
- personne sans ouverture ni interaction

---

## 11. Impacts directs sur les modules de la plateforme

### 11.1 Moteur de campagnes

Il doit gerer :

- editions recurrentes
- challenge sur 3 jours
- cohorte `EU`
- cohorte `US-CA`
- messages par jour et par statut

### 11.2 Integrations

Il doit gerer :

- lien StreamYard variable a chaque edition
- rattachement du bon lien au bon public
- prise en compte du fait que le lien est prepare a l'avance et diffuse par email puis dans les groupes pendant le challenge

### 11.3 IA conversationnelle

Elle doit gerer :

- FAQ de debutants
- clarifications simples
- objections financieres
- objections de confiance et de peur de perdre l'argent
- demandes de plan de paiement
- questions sur la prochaine edition du challenge
- bascule vers humain si necessaire

### 11.4 Dashboard

Il doit afficher :

- edition active
- repartition EU / US-CA
- presence par jour
- clics sur liens live
- FAQ dominantes
- objections financieres detectees
- file prioritaire de relances

---

## 12. Recommandation finale

Le `Challenge Amazon FBA` doit etre traite comme un objet metier specifique de la plateforme, et non comme une simple campagne generique.

Ses particularites structurantes sont :

- son format sur 3 jours
- sa recurrence bi-mensuelle
- ses deux cohortes horaires
- ses liens StreamYard variables
- son audience debutante
- ses objections financieres dominantes

Ces caracteristiques doivent etre encodees explicitement dans :

- le moteur de campagnes
- le scoring
- la segmentation
- le service conversationnel
- le dashboard
- l'Improvement Lab

Ce document constitue la base fonctionnelle concrete pour implementer le challenge de facon coherent, mesurable et scalable.
