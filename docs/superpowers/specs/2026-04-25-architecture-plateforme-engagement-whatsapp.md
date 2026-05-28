# Architecture de la plateforme d'engagement WhatsApp

**Date :** 2026-04-25  
**Source :** `cahier-des-charges-whatsapp-fba.docx`  
**Objectif :** definir une architecture industrialisable pour une plateforme d'engagement WhatsApp autour des challenges Amazon FBA, avec un decoupage modulaire pouvant etre delegue a differents LLM ou equipes d'agents.

---

## 1. Objectif produit

La plateforme doit couvrir tout le cycle d'engagement des inscrits au challenge afin de les transformer en participants reels aux lives puis en opportunites de conversion apres live. Elle doit automatiser les relances personnalisees sur WhatsApp, segmenter les contacts selon leur niveau d'engagement, fournir un assistant IA pour la gestion conversationnelle et exposer un tableau de bord operationnel pour le suivi humain.

La cible n'est pas un prototype rapide. La cible est une plateforme durable, industrialisable et evolutive, capable d'accueillir de nouvelles integrations, de nouveaux parcours de campagne et de nouveaux workflows conversationnels sans remise a plat du coeur du systeme.

### 1.1 Parametres metier confirmes

Les informations metier confirmees a date sont les suivantes :

- le nom officiel du programme est `Challenge Amazon FBA`
- le challenge se deroule sur `3 jours`, du `jeudi au samedi`
- le challenge a lieu `2 fois par mois`
- deux audiences doivent etre gerees separement : `US/CA` et `EU`
- les horaires de live sont differencies :
  - `21h00 Europe`
  - `19h00 Montreal / New York`
- les liens de connexion `StreamYard` changent a chaque edition du challenge
- les inscrits sont majoritairement `debutants`
- les objections principales sont `financieres`
- les questions frequentes identifiees a ce stade sont :
  - comment rejoindre le groupe WhatsApp
  - je me suis inscrit mais je n'ai pas recu d'email
  - quand est-ce que cela commence
  - combien coute la formation

Ces parametres doivent maintenant etre traites comme des exigences fonctionnelles du moteur de campagnes, du module d'integration StreamYard, du service conversationnel et du dashboard operateur.

---

## 2. Direction architecturale

La direction retenue est une plateforme modulaire par domaines, avec une dose controlee de traitement asynchrone.

Cela signifie :

- la logique metier centrale vit dans des services applicatifs sous ownership explicite
- les integrations sont isolees derriere des adaptateurs et des contrats clairs
- les traitements asynchrones passent par des files et des workers
- n8n est utilise comme outil d'orchestration et d'integration, mais pas comme source de verite du coeur metier
- les capacites LLM restent bornees aux modules conversationnels et d'assistance, jamais aux decisions metier autoritaires

Cette direction permet d'obtenir une structure a la fois industrialisable et facilement delegable a plusieurs LLM.

---

## 3. Architecture organisationnelle

L'organisation recommandee est une organisation par domaines metier, et non par couches techniques. Chaque domaine possede sa logique, ses interfaces, ses frontieres de persistence, ses tests et ses regles d'exploitation.

### 3.1 Platform Core

Responsabilites :

- standards techniques transverses
- authentification et autorisation admin
- configuration et gestion des environnements
- audit et gouvernance de plateforme
- conventions partagees et contrats inter-modules

### 3.2 Contacts et identite

Responsabilites :

- creation et mise a jour des contacts
- normalisation des numeros et resolution d'identite
- attribution de la source d'acquisition
- suivi du cycle de vie du contact
- historique du contact

### 3.3 Consentement et conformite

Responsabilites :

- gestion des opt-in et opt-out
- preuve de consentement
- validation de l'eligibilite d'un contact a etre sollicite
- controles de conformite lies a la messagerie

### 3.4 Campagnes et orchestration des parcours

Responsabilites :

- definition des sequences J-7 a J+2 et du deroule du challenge sur 3 jours
- conditions d'entree et de sortie
- regles de planification des etapes
- embranchements selon le comportement
- pilotage du cycle de vie des campagnes
- gestion de plusieurs editions du challenge par mois
- gestion des variantes horaires par region cible

### 3.5 Scoring et segmentation

Responsabilites :

- regles de calcul du score d'engagement
- recalcul du score
- attribution du segment
- historique des scores et segments
- versionnement des regles

### 3.6 IA conversationnelle

Responsabilites :

- automatisation des FAQ
- classification d'intention
- generation de reponses encadrees
- resume de conversation
- detection de l'escalade vers un humain
- adaptation du ton et des reponses a une audience majoritairement debutante
- traitement explicite des objections financieres

### 3.7 Hub d'integrations

Responsabilites :

- ingestion depuis Systeme.io
- ingestion des evenements Stripe et PayPal
- synchronisation StreamYard
- synchronisation email optionnelle
- normalisation des evenements externes
- gestion des liens de live variables a chaque nouvelle session

### 3.8 Operations messaging

Responsabilites :

- envoi et reception des messages WhatsApp
- suivi de livraison
- logique de retry
- abstraction du fournisseur
- support de replay et de diagnostic

### 3.9 Dashboard et reporting

Responsabilites :

- vues operationnelles du dashboard
- performance des campagnes
- visibilite au niveau contact
- files de relance manuelle
- exports et KPI

### 3.10 Ops et observabilite

Responsabilites :

- logs et traces
- supervision de sante
- alertes
- outillage de replay
- analyse d'incidents

---

## 4. Architecture technique par modules

La plateforme doit etre decoupee en modules explicites avec des frontieres nettes.

### 4.1 API Gateway

Responsabilites :

- point d'entree unique pour le dashboard et les clients admin
- exposition controlee des endpoints internes
- verification d'authentification et routage

Contraintes :

- pas de logique metier profonde

### 4.2 Registre des contacts

Responsabilites :

- creer et mettre a jour les contacts
- fusionner les doublons
- enrichir les profils
- maintenir l'etat et l'historique des contacts

### 4.3 Module Consentement et conformite

Responsabilites :

- stocker la preuve de consentement
- appliquer les regles d'opt-out
- decider l'eligibilite d'un contact a etre sollicite

Contraintes :

- tout envoi de campagne doit passer par cette couche

### 4.4 Moteur de campagnes

Responsabilites :

- definir les templates de campagnes et les parcours reels
- evaluer les regles d'entree, de branchement et d'arret
- rattacher les etapes de messages aux declencheurs comportementaux
- gerer les editions recurrentes du `Challenge Amazon FBA`
- gerer les sessions `EU` et `US/CA` avec des horaires distincts
- rattacher chaque contact a la bonne fenetre horaire et a la bonne edition du challenge

Contraintes :

- logique deterministe uniquement
- aucune dependance LLM pour les decisions metier autoritaires

### 4.5 Ordonnanceur de workflows

Responsabilites :

- planifier les delais et les taches differees
- gerer les retries et les fenetres d'execution
- dispatcher les jobs vers les workers

### 4.6 Livraison messaging

Responsabilites :

- envoyer et recevoir les messages WhatsApp
- suivre les statuts de livraison du fournisseur
- abstraire les details specifiques a Wati ou 360dialog
- gerer retries, echecs et replays

### 4.7 Journal d'evenements et d'interactions

Responsabilites :

- enregistrer tous les evenements metier et conversationnels utiles
- conserver une trace chronologique exploitable
- alimenter replay, scoring, reporting et audit

### 4.8 Moteur de scoring

Responsabilites :

- calculer le score d'engagement a partir de regles explicites
- stocker l'historique des evolutions du score
- versionner la logique de scoring

### 4.9 Moteur de segmentation

Responsabilites :

- attribuer les segments d'engagement
- mettre a jour le segment apres changement de score
- conserver l'historique de segmentation

### 4.10 Service d'IA conversationnelle

Responsabilites :

- repondre aux FAQ bornees
- classer l'intention utilisateur
- generer des reponses controlees
- produire des resumes de conversation
- recommander une escalade
- gerer un corpus FAQ centre sur les debutants
- reconnaitre et traiter les objections financieres

Contraintes :

- ce service ne doit pas porter l'etat metier autoritaire

### 4.11 Module d'escalade humaine

Responsabilites :

- creer des tickets ou actions de reprise manuelle
- prioriser les cas
- transferer les conversations non resolues aux humains

### 4.12 Connecteurs d'integration

Responsabilites :

- recevoir les webhooks externes
- normaliser les payloads
- emettre des evenements internes vers les modules metier

Contrainte :

- chaque connecteur suit le meme contrat `ingest-normalize-emit`

### 4.13 Read model du dashboard

Responsabilites :

- maintenir des vues optimisees pour la lecture dans le dashboard
- fournir des lectures operationnelles rapides

### 4.14 Reporting et analytics

Responsabilites :

- calculer les KPI de campagne
- mesurer engagement et tendances de conversion
- exposer les donnees de reporting

### 4.15 Console d'administration

Responsabilites :

- vues operateurs
- relances et actions manuelles
- gestion des escalades
- supervision des campagnes et contacts

### 4.16 Observabilite et audit

Responsabilites :

- logs structures
- metriques
- traces
- pistes d'audit
- hooks d'alerte

---

## 5. Ce qui doit rester hors autorite LLM

Pour garder une plateforme robuste, les LLM ne doivent pas decider des changements d'etat autoritaires dans les domaines metier critiques.

Les elements suivants doivent rester deterministes et maitrises par l'application :

- score d'engagement final
- attribution officielle du segment
- declenchement et arret des campagnes
- validation du consentement
- eligibilite d'envoi
- etat transactionnel des contacts
- logique de retry de livraison
- etat d'audit et preuve de conformite
- decisions de securite et d'autorisation

Les LLM peuvent assister sur la conversation, la classification, les suggestions, les resumes et la generation de contenu, mais ils ne remplacent jamais le moteur metier autoritaire.

---

## 6. Mapping des modules vers les LLM

La plateforme peut etre deleguee a plusieurs LLM en attribuant un ownership stable par domaine.

### 6.1 LLM-1 Platform Core

Possede :

- API Gateway
- standards d'auth admin et de configuration
- contrats inter-modules

### 6.2 LLM-2 Contacts et conformite

Possede :

- Registre des contacts
- Consentement et conformite

### 6.3 LLM-3 Campagnes et automation

Possede :

- Moteur de campagnes
- Ordonnanceur de workflows
- logique des sequences J-7 a J+2

### 6.4 LLM-4 Messaging et fournisseurs

Possede :

- Livraison messaging
- abstraction fournisseur
- gestion des etats de livraison

### 6.5 LLM-5 Scoring et segmentation

Possede :

- Moteur de scoring
- Moteur de segmentation

### 6.6 LLM-6 IA conversationnelle

Possede :

- Service d'IA conversationnelle
- logique FAQ
- gestion des intentions
- resume et recommandation d'escalade

### 6.7 LLM-7 Integrations

Possede :

- connecteur Systeme.io
- connecteur Stripe et PayPal
- connecteur StreamYard
- synchronisation email optionnelle

### 6.8 LLM-8 Dashboard et read models

Possede :

- Read model du dashboard
- Reporting et analytics
- Console d'administration

### 6.9 LLM-9 Ops et observabilite

Possede :

- Observabilite et audit
- outils de monitoring et de replay

### 6.10 Regles de coordination

- chaque LLM possede un domaine et son contrat
- les changements cross-domain passent par des interfaces explicites
- les tables partagees et les evenements ont un ownership clair
- aucun LLM ne doit modifier silencieusement le modele coeur d'un autre domaine

---

## 7. Infrastructure cible

Le point de depart recommande pour une base industrialisable est le suivant :

- un VPS principal ou un compute cloud equivalent
- un reverse proxy avec Nginx ou Traefik
- des services conteneurises avec Docker Compose
- une trajectoire claire vers un orchestrateur plus avance si l'echelle le demande plus tard
- PostgreSQL comme base de donnees principale
- Redis pour le cache et le broker leger
- une file de jobs et des workers pour l'asynchrone
- n8n pour l'orchestration cote integrations
- une gestion securisee des variables d'environnement
- des sauvegardes base de donnees et workflows
- healthchecks, logs et alertes

### 7.1 Principes d'infrastructure

- les services FastAPI portent la logique metier
- PostgreSQL reste la source de verite metier
- Redis et les workers portent l'execution asynchrone
- n8n reste hors du coeur critique de l'etat metier
- sauvegardes et capacite de replay sont obligatoires des le depart

---

## 8. Flux principal de donnees

Le flux de reference est le suivant :

1. un lead ou inscrit entre via Systeme.io
2. le connecteur d'integration recoit l'evenement externe
3. le payload est normalise en evenement interne
4. le Registre des contacts cree ou met a jour le contact
5. le module Consentement et conformite verifie l'eligibilite d'envoi
6. le Moteur de campagnes inscrit le contact dans une edition pertinente du `Challenge Amazon FBA` et dans la bonne cohorte horaire
7. l'Ordonnanceur de workflows planifie les jobs associes
8. le module Livraison messaging envoie les messages WhatsApp via le fournisseur avec les bons messages de sequence et les bons liens StreamYard
9. les reponses entrantes et statuts fournisseurs sont ecrits dans le Journal d'evenements et d'interactions
10. le Moteur de scoring recalcule l'engagement
11. le Moteur de segmentation met a jour le segment
12. le Service d'IA conversationnelle traite les interactions bornees
13. le Module d'escalade humaine cree du travail operateur si necessaire
14. le Read model du dashboard met a jour les vues operationnelles
15. le Reporting et analytics expose les indicateurs de performance

---

## 9. Ordre de delivery

Pour reduire le risque systeme, l'implementation devrait suivre cet ordre :

1. Platform Core et fondations d'infrastructure
2. Contacts et consentement
3. Livraison messaging
4. Moteur de campagnes et ordonnanceur
5. Scoring et segmentation
6. Integrations externes
7. Dashboard et reporting
8. IA conversationnelle et escalade
9. Durcissement observabilite et outillage operationnel

Cet ordre garantit que l'ossature transactionnelle soit stable avant l'ajout des couches IA et analytiques plus avancees.

---

## 10. Criteres de robustesse

La plateforme n'est consideree prete pour la production que si elle integre :

- gestion idempotente des webhooks
- strategies explicites de retry pour les jobs et la messagerie
- logs structures et consultables
- historique d'evenements auditable
- capacite de replay sur les workflows echoues
- supervision des files, fournisseurs et services
- separation stricte entre etat metier deterministe et sorties LLM
- tests de contrat entre domaines
- visibilite operateur claire pour intervention manuelle
- application stricte des regles de consentement et d'opt-out

---

## 11. Structure recommandee du repository et de l'allocation du travail

Meme si l'implementation demarre dans un seul repository, le code doit etre organise selon les frontieres de domaines.

Structure cible suggeree :

```text
platform/
  services/
    api-gateway/
    contacts/
    consent/
    campaigns/
    messaging/
    scoring/
    segmentation/
    conversation-ai/
    integrations/
    dashboard/
    observability/
  shared/
    contracts/
    events/
    auth/
    config/
  infra/
    docker/
    nginx/
    n8n/
    backups/
    monitoring/
  docs/
    architecture/
    modules/
    runbooks/
```

Si l'implementation commence sous forme de monorepo modulaire, ces frontieres doivent quand meme etre preservees dans les dossiers, les contrats et les suites de tests afin de pouvoir separer les services plus tard sans rupture.

---

## 12. Recommandation finale

Le meilleur fit pour ce projet est une plateforme modulaire par domaines, avec des services metier deterministes, une execution asynchrone controlee, des integrations isolees et un usage LLM strictement borne.

Cette architecture apporte :

- une base durable
- des frontieres d'ownership claires pour la delegation aux LLM
- une meilleure capacite de passage a l'echelle
- une observabilite et une recuperation plus solides
- un risque plus faible de fragilite lie a une surdependance a n8n ou aux LLM dans le coeur metier

Cette architecture peut maintenant etre traduite en plan d'execution detaille, decoupe par domaines, infrastructure, interfaces, tests et jalons de delivery.

---

## 13. Boucle d'amelioration continue inspiree de Karpathy

Deux references sont pertinentes pour cette plateforme :

- `forrestchang/andrej-karpathy-skills` pour discipliner le comportement des agents de dev et des LLM qui implementent les modules
- `karpathy/autoresearch` pour inspirer une boucle d'amelioration automatique offline sur les conversations, prompts, regles de classification et micro-optimisations fonctionnelles

### 13.1 Usage recommande de `andrej-karpathy-skills`

Ce repository n'est pas une feature produit. C'est un cadre de travail pour les agents.

Il peut etre applique a :

- la production de code par les LLM
- la limitation de la sur-ingenierie
- la clarification des hypotheses avant implementation
- les modifications chirurgicales module par module
- l'execution orientee objectif avec verification explicite

Son role est de reduire les erreurs de conception et de garder des modules simples, bornes et testables.

### 13.2 Usage recommande de `autoresearch`

Le bon usage ici n'est pas de laisser une boucle autonome modifier la production en direct.

Le bon usage est de creer un `Continuous Improvement Lab` offline qui :

- collecte des conversations anonymisees ou pseudonymisees
- extrait des cas d'usage frequents, des echecs de classification, des escalades et des points de friction
- propose des variantes de prompts, regles de routage, heuristiques FAQ, textes de reponse et micro-regles de segmentation non critiques
- evalue ces variantes sur un jeu de validation offline
- conserve uniquement les ameliorations mesurables
- soumet ensuite ces ameliorations a une revue humaine avant promotion en production

### 13.3 Ce que cette boucle peut ameliorer

- prompts de l'agent conversationnel
- classification d'intention
- detection d'escalade
- suggestions de reponse
- formulations des messages automatises
- heuristiques de priorisation dans la file operateur
- micro-regles de scoring candidates, tant qu'elles sont validees humainement avant activation
- traitements de FAQ debutants
- reponses aux objections financieres
- optimisation des messages des 3 jours du challenge
- optimisation par zone horaire `EU` vs `US/CA`

### 13.4 Ce que cette boucle ne doit pas modifier directement

- logique de consentement
- eligibilite d'envoi
- etat transactionnel des contacts
- regles finales de segmentation en production sans validation humaine
- mecanismes de retry provider
- politiques de securite, auth et audit

### 13.5 Nouveau sous-systeme recommande

Ajouter un sous-systeme dedie :

- `Improvement Lab`

Responsabilites :

- constituer les datasets d'evaluation a partir des conversations
- versionner prompts, policies et heuristiques candidates
- executer des campagnes d'evaluation offline
- comparer les variantes selon des metriques cibles
- publier un rapport de gain ou de regression
- proposer des candidats de release au `Platform Core`

### 13.6 Metriques de pilotage du lab

- taux de bonne classification d'intention
- taux d'escalade pertinente
- reduction des escalades inutiles
- qualite percue des reponses
- taux de conversion post-interaction
- temps de resolution operateur
- taux d'erreur ou de non-reponse

### 13.7 Gouvernance de mise en production

Le `Improvement Lab` peut proposer.
Le `Platform Core` et les owners metier valident.
La production n'adopte que les versions :

- evaluees offline
- tracees
- reversibles
- approuvees humainement
