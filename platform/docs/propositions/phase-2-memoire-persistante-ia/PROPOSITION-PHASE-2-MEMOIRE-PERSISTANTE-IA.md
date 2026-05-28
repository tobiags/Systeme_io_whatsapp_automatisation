# Proposition Phase 2 - Memoire Persistante IA

## Contexte

La phase 1 a permis de mettre en place le socle operationnel du systeme :

- capture des leads depuis Systeme.io
- orchestration n8n
- webhooks StreamYard
- scoring et segmentation
- agent conversationnel
- relances conditionnelles
- file humaine / closers

Le systeme est maintenant capable d'automatiser et de suivre l'engagement.  
La prochaine evolution naturelle consiste a renforcer la qualite conversationnelle de l'IA avec une **memoire persistante par prospect**.

## Objectif

Ajouter une couche de memoire persistante pour que l'IA :

- garde le contexte d'un prospect d'une conversation a l'autre
- evite de reposer les memes questions
- adapte mieux son ton et ses relances
- retienne les objections, blocages et signaux d'interet
- transmette un meilleur niveau d'information aux closers

## Pourquoi cette evolution est utile

Aujourd'hui, l'IA peut repondre et relancer correctement a partir des regles et de l'historique recent.  
Avec une memoire persistante, elle devient plus coherente dans la duree.

Exemples de gains :

- un prospect qui explique qu'il travaille le soir n'est plus relance comme quelqu'un de disponible
- un debutant n'est plus relance comme un vendeur deja lance
- une objection budget ou confiance peut etre retenue et traitee au bon moment
- un closer recupere un brief plus riche avant de reprendre la conversation

## Ce que la memoire conservera

### 1. Resume contact

Une fiche synthese mise a jour automatiquement :

- niveau d'experience
- blocage principal
- disponibilite
- interet pour l'offre
- signaux d'achat
- besoin d'escalade humaine
- resume court de la relation

### 2. Faits stables

Des informations structurees et reutilisables :

- "debutant"
- "deja lance"
- "indisponible le soir"
- "interesse mais bloque par budget"
- "veut parler a un closer"

### 3. Boucles ouvertes

Les sujets a reprendre plus tard :

- question restee sans reponse
- objection non traitee
- promesse de rappel
- demande de formulaire ou de call

## Impact attendu

Cette phase doit permettre :

- des conversations plus naturelles
- moins de repetitions
- une meilleure personnalisation
- une meilleure qualification des prospects
- un meilleur taux de transformation vers les lives et vers les closers

## Ce qui change dans le systeme

### Donnees

Ajout d'une memoire persistante par contact dans la base :

- resume conversationnel
- faits stables
- niveau d'interet
- blocages identifies
- dernier brief IA

### Agent IA

L'agent ne repondra plus uniquement sur la base du dernier message.  
Il repondra avec :

- le message courant
- le resume memoire du contact
- les faits stables identifies
- les regles metier du systeme

### Dashboard

Le dashboard pourra afficher un contexte plus utile pour les operateurs et les closers :

- resume du prospect
- objections principales
- niveau de chaleur
- raisons d'absence ou de hesitation

## Ce que cette phase n'est pas

Cette phase n'est pas un simple historique brut des messages.  
L'objectif n'est pas d'empiler des transcripts, mais de maintenir une **memoire structuree, compacte et exploitable**.

Elle ne remplace pas non plus les regles metier existantes.  
Elle vient les renforcer.

## Perimetre recommande

### Inclus

- schema de memoire persistante
- resume automatique par contact
- extraction de faits stables
- injection de la memoire dans le contexte de l'agent
- affichage des elements utiles dans le dashboard

### Hors perimetre initial

- moteur de contradiction avance
- moteur de recherche semantique complet
- knowledge base globale type wiki d'entreprise

Ces briques pourront venir ensuite si besoin.

## Recommandation

Cette phase est recommande apres validation complete de la phase 1.

Pourquoi :

- le socle d'automatisation doit d'abord etre stabilise
- les vrais cas conversationnels doivent etre observes
- la memoire doit etre concue a partir des objections et comportements reels

En pratique, la memoire persistante est une **evolution de qualite et de performance**, pas un prerequis pour faire fonctionner le systeme actuel.

## Proposition de mise en oeuvre

1. cadrage fonctionnel de la memoire
2. ajout du schema de donnees
3. mise a jour de l'agent IA
4. ajout des resumes contact dans le dashboard
5. tests sur conversations reelles
6. ajustements apres observation terrain

## Conclusion

La phase 2 "Memoire Persistante IA" vise a rendre le systeme plus intelligent, plus coherent et plus utile commercialement.

La phase 1 rend le systeme operationnel.  
La phase 2 rend les conversations plus fines, plus pertinentes et plus rentables dans la duree.
