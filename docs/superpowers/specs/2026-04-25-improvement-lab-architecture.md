# Architecture du sous-systeme Improvement Lab

**Date :** 2026-04-25  
**Contexte :** extension de la plateforme d'engagement WhatsApp pour ajouter une boucle d'amelioration continue inspiree des approches de type `autoresearch`, appliquee en mode offline et sous validation humaine.  
**Objectif :** proposer au proprietaire du projet un sous-systeme independant capable d'ameliorer en continu les conversations, les sequences de challenges, les prompts et certaines heuristiques fonctionnelles sans mettre en risque le coeur metier de production.

---

## 1. Role du sous-systeme

`Improvement Lab` est un sous-systeme separe du coeur transactionnel. Il observe les conversations, les parcours de challenge et les performances des reponses automatisees, puis il produit des hypotheses d'amelioration mesurables.

Son role n'est pas de modifier directement la production. Son role est de :

- collecter et preparer des donnees d'evaluation
- tester des variantes de prompts, de messages, de policies et d'heuristiques
- mesurer les gains ou regressions
- recommander des promotions en production
- fournir un cadre de validation humaine avant activation

---

## 2. Positionnement dans l'architecture globale

Le sous-systeme doit vivre a cote de la plateforme principale, pas a l'interieur du coeur metier critique.

Il consomme :

- journaux de conversations
- evenements de campagnes
- historiques de segmentation
- performances des messages
- escalades humaines
- retours operateurs

Il produit :

- rapports d'evaluation
- variantes recommandees
- alertes de regression
- propositions de mise a jour
- syntheses hebdomadaires d'amelioration

Il ne doit jamais ecrire directement dans :

- consentement
- etat transactionnel des contacts
- eligibilite d'envoi
- regles critiques de campagne en prod
- regles finales de securite, auth et audit

---

## 3. Sous-composants obligatoires

### 3.1 Improvement Lab

C'est l'orchestrateur global du sous-systeme.

Responsabilites :

- piloter les campagnes d'evaluation
- coordonner datasets, variantes, executeurs et rapports
- versionner les experiences
- suivre l'historique des gains et regressions

### 3.2 Conversation Evaluation Dataset

Ce composant maintient les jeux de donnees d'evaluation conversationnelle.

Responsabilites :

- extraire des conversations anonymisees ou pseudonymisees
- etiqueter les intentions, escalades, objections et outcomes
- constituer des jeux de validation et de regression
- separer les datasets par cas d'usage : FAQ, vente, objections, support, escalade

Exemples d'elements suivis :

- message utilisateur
- intention attendue
- besoin d'escalade attendu
- qualite de reponse attendue
- segment du contact
- contexte de challenge
- zone cible `EU` ou `US/CA`
- profil `debutant`
- presence d'une objection financiere

### 3.3 Challenge Messaging Lab

Ce composant est dedie aux sequences de challenge J-7 a J+2 et au deroule reel du `Challenge Amazon FBA` sur 3 jours.

Responsabilites :

- tester des variantes de messages
- comparer les accroches, CTA, rappels et suivis post-live
- analyser les taux de reponse, de confirmation, de presence et de conversion
- proposer des optimisations par segment et par etape du challenge

Exemples d'objets testes :

- message de bienvenue J-7
- message de confirmation de presence J-3
- rappel J-1
- relance du matin du live
- suivi J+1 et J+2
- variantes `EU` vs `US/CA`
- messages lies aux sessions `jeudi`, `vendredi`, `samedi`
- gestion des messages incorporant les liens StreamYard variables

### 3.4 Prompt Registry

Ce composant versionne tous les artefacts textuels et logiques experimentaux.

Responsabilites :

- stocker prompts, policies, heuristiques et variantes
- tracer version, auteur, date, score et statut
- distinguer `draft`, `tested`, `approved`, `rejected`, `promoted`
- permettre le rollback vers une version precedente

Le Prompt Registry doit couvrir :

- prompts conversationnels
- prompts de classification
- prompts de resume
- variantes de messages de challenge
- heuristiques candidates de priorisation et d'escalade

### 3.5 Offline Experiment Runner

C'est le moteur d'execution des experiences.

Responsabilites :

- lancer les evaluations offline
- comparer les variantes sur jeux de validation
- calculer les scores et metriques
- generer les rapports de resultats
- enregistrer les comparaisons dans le registre

Le runner doit pouvoir executer plusieurs types d'experiences :

- evaluation de prompts
- comparaison A/B offline
- benchmark de classification
- evaluation de policies d'escalade
- evaluation de sequences de messaging

### 3.6 Human Approval Gate

C'est la porte de gouvernance obligatoire avant toute promotion en production.

Responsabilites :

- presenter les changements proposes
- afficher les gains, risques et regressions detectees
- demander une validation explicite
- journaliser qui a valide, quand, et sur quelle base
- empecher toute promotion automatique non approuvee

Ce composant est central. Sans lui, l'Improvement Lab devient dangereux.

---

## 4. Domaines ou appliquer la methodologie autoresearch

Les meilleurs candidats sont :

- conversations WhatsApp
- classification d'intention
- detection des cas hors perimetre
- detection d'escalade humaine
- prompts de reponse
- formulations de messages des challenges
- relances J-7 a J+2
- analyse des objections
- priorisation de la file operateur
- suggestions de prochaine action
- adaptation des reponses a une audience debutante
- optimisation des variantes horaires `EU` et `US/CA`
- traitement des FAQ client confirmees

Ces domaines ont trois avantages :

- ils sont mesurables
- ils sont reversibles
- ils ne touchent pas directement aux verites metier critiques

---

## 5. Domaines a exclure du pilotage automatique

Le sous-systeme ne doit jamais appliquer automatiquement des changements sur :

- consentement et opt-out
- eligibilite d'envoi
- etat transactionnel officiel des contacts
- politiques de securite
- audit de conformite
- retries provider
- segmentation officielle en production sans validation humaine
- scoring officiel sans validation humaine

La regle simple est :

`Improvement Lab peut proposer. La plateforme de production decide.`

---

## 6. Architecture de donnees du sous-systeme

Le sous-systeme doit avoir son propre stockage logique.

Tables ou collections recommandees :

- `evaluation_datasets`
- `dataset_samples`
- `prompt_candidates`
- `message_variants`
- `experiment_runs`
- `experiment_scores`
- `approval_requests`
- `approval_decisions`
- `release_recommendations`
- `weekly_summaries`
- `notification_events`

Chaque execution doit etre traquee avec :

- identifiant d'experience
- variante testee
- dataset utilise
- metriques observees
- baseline de comparaison
- resultat final
- statut d'approbation

---

## 7. Dashboard dedie : oui, c'est recommande

Oui, ce sous-systeme merite un dashboard separe.

La raison est simple : ce n'est pas un dashboard de production operationnelle. C'est un dashboard d'amelioration continue, de gouvernance experimentale et de pilotage des apprentissages.

Le melanger au dashboard principal rendrait les choses confuses pour les operateurs.

Le dashboard dedie doit montrer :

- variantes testees
- experiences en cours
- scores vs baseline
- regressions detectees
- suggestions en attente d'approbation
- historique des promotions en production
- backlog des idees d'amelioration
- datasets disponibles et leur couverture

### 7.1 Vues recommandees

- `Overview`
- `Experiments`
- `Prompt Registry`
- `Challenge Messaging`
- `Conversation Quality`
- `Approvals`
- `Notifications`
- `Weekly Reports`

---

## 8. Systeme de notification : oui, indispensable

Oui, il faut un systeme de notification dedie.

Le lab doit pousser des notifications quand :

- une experience montre un gain significatif
- une regression importante est detectee
- un candidat est pret pour revue
- une approbation humaine est requise
- une variante promue degrade la performance post-release
- un dataset devient obsolete ou insuffisant

Canaux possibles :

- email
- Slack
- WhatsApp interne si pertinent
- centre de notifications dans le dashboard

Types de notifications :

- `info`
- `review_required`
- `regression_alert`
- `promotion_ready`
- `rollback_recommended`

---

## 9. Recapitulatif hebdomadaire : fortement recommande

Oui, un recapitulatif hebdomadaire est meme une excellente idee.

Il sert au proprietaire du projet, au responsable produit et au responsable operations pour voir :

- ce qui a ete teste
- ce qui a progresse
- ce qui a regresse
- ce qui merite validation
- ce qui a ete promu en production
- l'impact estime ou observe sur les conversations et les challenges

### 9.1 Contenu recommande du recap hebdomadaire

- nombre d'experiences executees
- top 5 gains detectes
- top 5 regressions detectees
- variantes recommandees pour promotion
- variantes rejetees
- nouveaux patterns conversationnels observes
- nouvelles objections detectees
- evolution du taux d'escalade
- evolution du taux de reponse
- evolution du taux de confirmation de presence live
- evolution du taux de conversion post-live
- comparaison des performances `EU` vs `US/CA`
- impact des variantes sur les objections financieres
- nouvelles FAQ detectees chez les debutants

### 9.2 Formats possibles

- email hebdomadaire automatique
- PDF exportable
- page dediee dans le dashboard
- digest Slack

Le meilleur choix initial est :

- page dashboard dediee
- email hebdomadaire automatique

---

## 10. Metriques de pilotage

Le sous-systeme doit suivre au minimum :

- precision de classification d'intention
- precision de detection d'escalade
- taux d'escalades pertinentes
- reduction des escalades inutiles
- taux de reponse utilisateur
- taux de confirmation de presence
- taux de presence au live
- taux de conversion post-live
- temps moyen de reprise operateur
- taux d'acceptation des promotions recommandees
- taux de rollback apres promotion

---

## 11. Ownership recommande

Le sous-systeme peut etre porte par un bloc LLM ou une mini-equipe dediee.

Ownership recommande :

- `LLM-6` pour les prompts conversationnels et les policies d'escalade
- `LLM-8` pour le dashboard dedie et les rapports
- `LLM-9` pour l'observabilite, la tracabilite et les notifications
- `LLM-1` pour la gouvernance et l'integration avec le Platform Core

---

## 12. Proposition commerciale a faire au proprietaire

Ce sous-systeme peut etre presente comme une brique premium de scalabilite.

Positionnement possible :

- la plateforme principale automatise et opere
- l'Improvement Lab apprend, mesure et optimise
- le systeme devient meilleur chaque semaine sans casser la production

Valeur pour le proprietaire :

- meilleure qualite des conversations
- meilleures sequences de challenge
- meilleure conversion
- meilleure supervision des changements
- meilleure capacite d'apprentissage produit

---

## 13. Recommandation finale

Oui, il faut creer ce document et proposer ce sous-systeme comme une extension strategique.

Oui, il faut un dashboard separe.

Oui, il faut un systeme de notifications.

Oui, il faut un recapitulatif hebdomadaire.

La bonne architecture est :

- un `Improvement Lab` hors production live
- un `Conversation Evaluation Dataset`
- un `Challenge Messaging Lab`
- un `Prompt Registry`
- un `Offline Experiment Runner`
- un `Human Approval Gate`
- un dashboard dedie
- un centre de notifications
- un recapitulatif hebdomadaire automatique

Cela permet de faire scaler l'infrastructure intelligemment, sans transformer la production en terrain d'experimentation non controle.
