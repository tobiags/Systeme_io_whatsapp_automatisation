# Runbook de recette orchestrateur - Plateforme WhatsApp Challenge Amazon FBA

**Date :** 2026-04-27  
**Objet :** fournir a l'orchestrateur un parcours de test clair pour verifier chaque feature, constater les resultats attendus, identifier les bugs et remonter des retours exploitables pour correction.  
**Usage :** ce document sert de guide de recette fonctionnelle, de validation operationnelle et de support de feedback.

---

## 1. Objectif du document

Ce document te permet de :

- tester chaque feature dans le bon ordre
- savoir exactement quoi faire
- savoir ce que tu dois voir comme resultat
- detecter rapidement ce qui ne fonctionne pas
- remonter des retours precis pour correction

L'objectif n'est pas seulement de dire `ca marche` ou `ca ne marche pas`.
L'objectif est de produire un retour exploitable, module par module, scenario par scenario.

---

## 2. Regles de recette

Pendant les tests :

- tester une chose a la fois
- noter l'heure du test
- noter la feature testee
- noter la donnee d'entree exacte
- noter ce qui etait attendu
- noter ce qui a reellement eu lieu
- capturer si possible une preuve : capture, log, message recu, absence de message, erreur visible

Quand un bug est detecte, il faut toujours pouvoir repondre a ces 5 questions :

1. `Qu'est-ce que j'ai fait ?`
2. `Qu'est-ce qui etait cense se passer ?`
3. `Qu'est-ce qui s'est passe reellement ?`
4. `A quel moment exact cela a casse ?`
5. `Est-ce bloquant ou contournable ?`

---

## 3. Ordre recommande de recette

Tester dans cet ordre :

1. Contacts et cohortes
2. Consentement
3. Affectation edition / challenge
4. Messages pre-challenge
5. Jour 1
6. Jour 2
7. Jour 3
8. FAQ
9. Objections financieres et post-live
10. Segmentation
11. Priorisation operateur
12. Dashboard
13. Improvement Lab si active

Cet ordre permet d'isoler les problemes de fond avant de tester les couches plus visibles.

---

## 4. Prerequis avant test

Avant toute recette, verifier :

- acces Wati fonctionnel
- edition de challenge creee
- deux cohortes disponibles : `EU` et `US-CA`
- liens StreamYard renseignes pour l'edition en cours
- listes Systeme.io disponibles
- environnement de test clairement identifie
- numeros de test disponibles
- dashboard accessible
- logs ou traces consultables si besoin

Si un prerequis manque, ne pas lancer de test dependant de ce prerequis.

---

## 5. Jeux de profils de test a preparer

Preparer idealement ces profils :

- `Profil A - Froid EU`
- `Profil B - Tiede EU`
- `Profil C - Chaud EU`
- `Profil D - Tres chaud EU`
- `Profil E - Froid US-CA`
- `Profil F - Chaud US-CA`
- `Profil G - Objection budget`
- `Profil H - Demande plan de paiement`
- `Profil I - Paiement echoue`
- `Profil J - Sceptique`
- `Profil K - Demande prochaine edition`

Chaque profil doit avoir :

- un nom ou identifiant de test
- un numero WhatsApp
- une cohorte connue
- une edition de challenge connue
- un historique minimal attendu

---

## 6. Parcours de test par feature

### Feature 1 - Import contacts et cohortes

**But**

Verifier qu'un inscrit entre bien dans le systeme avec la bonne cohorte.

**Procedure**

1. importer ou synchroniser un contact depuis la liste `EU`
2. verifier sa creation dans la plateforme
3. verifier que sa cohorte est `EU`
4. refaire avec un contact `US-CA`

**Resultat attendu**

- le contact existe
- la source Systeme.io est visible
- la cohorte rattachee est correcte
- aucune confusion `EU` / `US-CA`

**Ce que tu dois voir**

- fiche contact creee
- champ `cohorte`
- champ `edition`
- horodatage d'entree

**Reponse systeme attendue**

- contact cree sans erreur
- aucune duplication non justifiee

**Bug possible**

- contact non cree
- mauvaise cohorte
- doublon
- edition absente

**Feedback attendu si bug**

`Contact test X importe depuis liste EU, cree avec cohorte US-CA au lieu de EU. Bug bloquant sur affectation.`

---

### Feature 2 - Consentement

**But**

Verifier qu'un contact eligible peut recevoir les messages.

**Procedure**

1. ouvrir un contact de test
2. verifier la presence du consentement
3. simuler un contact sans consentement
4. verifier qu'aucune sequence ne part si le consentement manque

**Resultat attendu**

- contact avec consentement : eligible
- contact sans consentement : bloque

**Ce que tu dois voir**

- statut consentement
- statut eligibilite
- eventuel blocage d'envoi

**Bug possible**

- message envoye sans consentement
- contact eligible bloque a tort

---

### Feature 3 - Affectation edition du challenge

**But**

Verifier qu'un contact est rattache a la bonne edition.

**Procedure**

1. choisir une edition active
2. rattacher un contact test a cette edition
3. verifier date, cohorte et liens associes

**Resultat attendu**

- edition correcte
- calendrier associe
- lien live correspondant a l'edition

**Bug possible**

- edition incorrecte
- edition vide
- lien d'une autre session

---

### Feature 4 - Sequence pre-challenge

**But**

Verifier les messages de bienvenue, orientation, groupe WhatsApp et rappel de demarrage.

**Procedure**

1. inscrire un contact test
2. observer la sequence immediate
3. verifier les messages recus
4. verifier le contenu et l'ordre

**Resultat attendu**

- message de bienvenue recu
- rappel de cohorte recu
- instruction groupe WhatsApp recu
- rappel sur l'email/lien recu

**Ce que tu dois voir**

- horodatage des messages
- bon wording
- bonne personnalisation

**Bug possible**

- message manquant
- mauvais ordre
- mauvaise cohorte mentionnee
- variable vide

**Reponse a verifier**

- prenom correctement injecte
- bon fuseau mentionne
- pas de lien vide

---

### Feature 5 - Jour 1

**But**

Verifier les automatismes Jour 1 avant, juste avant et apres le live.

**Procedure**

1. prendre un contact de test dans l'edition active
2. attendre ou simuler les jalons `H-6`, `H-45`, `H-10`, `post-live`
3. verifier tous les messages

**Resultat attendu**

- rappel Jour 1 recu
- lien StreamYard recu
- dernier rappel recu
- recap post-live recu

**Ce que tu dois voir**

- bon lien StreamYard
- bon horaire
- sequence coherente

**Bug possible**

- lien absent
- lien faux
- message trop tot ou trop tard
- recap non recu

---

### Feature 6 - Jour 2

**But**

Verifier les relances et re-engagements du Jour 2.

**Procedure**

1. utiliser un profil present Jour 1
2. utiliser un profil absent Jour 1
3. comparer les messages recu le Jour 2

**Resultat attendu**

- le present recoit une relance de continuite
- l'absent recoit une relance de rattrapage
- le lien du Jour 2 est bien envoye

**Bug possible**

- meme message pour tous les profils
- aucune differenciation comportementale
- absence de re-engagement

---

### Feature 7 - Jour 3

**But**

Verifier la logique du dernier jour et la bascule vers le post-challenge.

**Procedure**

1. tester avec un profil tiede
2. tester avec un profil tres chaud
3. verifier relance finale et suivi apres live

**Resultat attendu**

- message final bien envoye
- lien correct
- suivi apres challenge visible

**Bug possible**

- aucune transition vers le post-challenge
- mauvais niveau d'urgence

---

### Feature 8 - FAQ

**But**

Verifier les reponses automatiques aux questions frequentes.

**Questions a tester**

- comment rejoindre le groupe WhatsApp
- je me suis inscrit mais je n'ai pas recu d'email
- quand cela commence
- combien coute la formation
- quand est-ce que vous referez un nouveau challenge

**Procedure**

1. envoyer chaque question via WhatsApp
2. observer la reponse
3. verifier si l'intention a bien ete comprise

**Resultat attendu**

- reponse correcte
- reponse courte
- pas de confusion entre FAQ et objection

**Bug possible**

- mauvaise comprehension
- reponse hors sujet
- reponse trop vague
- absence de reponse

---

### Feature 9 - Objections financieres

**But**

Verifier que le systeme distingue les differents types d'objections.

**Cas a tester**

- je n'ai pas le budget
- c'est trop cher
- je reviendrai plus tard
- je veux payer en 10 fois
- j'ai essaye de payer mais je n'avais pas assez
- j'ai peur de perdre mon argent

**Procedure**

1. envoyer chaque objection
2. verifier la reponse
3. verifier si le bon tag / evenement est pose
4. verifier s'il y a escalade ou file operateur

**Resultat attendu**

- la categorie d'objection est differenciee
- la reponse est adaptee
- un lead engage ne tombe pas dans l'oubli

**Bug possible**

- toutes les objections traitees pareil
- absence de suivi sur paiement echoue
- aucune priorisation operateur

**Resultat que tu dois voir**

- tag objection
- niveau de priorite
- eventuel ticket ou file manuelle

---

### Feature 10 - Segmentation challenge

**But**

Verifier que les segments evoluent selon les signaux reels.

**Procedure**

1. creer un profil inactif
2. creer un profil qui clique et rejoint un live
3. creer un profil qui participe et pose des questions prix
4. comparer les segments obtenus

**Resultat attendu**

- inactif = `froid`
- interesse mais limite = `tiede`
- participant engage = `chaud`
- participant engage avec signal commercial = `tres_chaud`

**Bug possible**

- segment incoherent
- objection financiere fait baisser a tort un lead tres engage

---

### Feature 11 - Priorisation operateur

**But**

Verifier que les cas importants remontent correctement.

**Cas a tester**

- plan de paiement demande
- paiement echoue
- sceptique apres live
- demande de prochaine edition
- FAQ simple sans enjeu commercial

**Resultat attendu**

- paiement echoue = priorite haute
- plan de paiement = priorite haute
- sceptique engage = priorite moyenne
- FAQ simple = priorite faible

**Bug possible**

- priorites plates
- mauvaise file
- aucun ticket

---

### Feature 12 - Dashboard

**But**

Verifier que le dashboard permet de suivre les operations.

**Procedure**

1. ouvrir le dashboard
2. verifier edition active
3. verifier repartition `EU` / `US-CA`
4. verifier contacts, messages, objections, escalades
5. verifier file manuelle

**Resultat attendu**

- chiffres visibles
- file de priorite visible
- objections visibles
- contacts filtrables

**Bug possible**

- donnees absentes
- dashboard non a jour
- absence des objections / escalades

---

### Feature 13 - Improvement Lab

**But**

Verifier que les experiences offline sont visibles et gouvernees.

**Procedure**

1. ouvrir le dashboard du lab si disponible
2. verifier qu'un prompt ou message candidat peut etre evalue
3. verifier qu'une recommandation ne passe pas en production sans validation humaine

**Resultat attendu**

- experience visible
- score visible
- statut `a valider` visible

**Bug possible**

- aucune trace de test
- promotion automatique

---

## 7. Tableau de retour de bug recommande

Quand tu me remontes un bug, utilise si possible ce format :

| ID bug | Feature | Scenario teste | Attendu | Observe | Gravite | Preuve |
|---|---|---|---|---|---|---|
| BUG-001 | Jour 1 | envoi lien H-45 EU | recevoir le lien StreamYard EU | aucun message recu | bloquant | capture + heure |

### Niveaux de gravite

- `bloquant` : empeche la feature de fonctionner
- `majeur` : fonctionne mal ou partiellement
- `mineur` : fonctionne mais comportement imparfait
- `cosmetique` : affichage, wording, detail non bloquant

---

## 8. Format de retour ideal a me renvoyer

Le meilleur format est :

```text
Feature :
Profil teste :
Cohorte :
Edition :
Action realisee :
Resultat attendu :
Resultat observe :
Heure du test :
Gravite :
Preuve :
Commentaire :
```

Exemple :

```text
Feature : Objections financieres
Profil teste : Profil I - Paiement echoue
Cohorte : EU
Edition : 2026-05-07
Action realisee : message "j'ai essaye de payer mais je n'avais pas assez"
Resultat attendu : tag payment_failed_insufficient_funds + priorite haute
Resultat observe : reponse generique budget, aucune priorite creee
Heure du test : 21:47
Gravite : majeur
Preuve : capture WhatsApp + capture dashboard
Commentaire : le systeme ne distingue pas le paiement echoue du simple manque de budget
```

---

## 9. Ce qui me permet de corriger vite

Les retours les plus utiles pour correction sont :

- une seule anomalie par retour
- le texte exact envoye
- la cohorte exacte
- l'heure exacte
- la capture de l'ecran ou du message
- le comportement attendu en une phrase

Les retours les moins utiles sont :

- `ca ne marche pas`
- `le bot est bizarre`
- `j'ai pas aime la reponse`

Il faut toujours rattacher le retour a une feature et a un scenario.

---

## 10. Recommandation de procedure de recette

Procedure simple a suivre :

1. choisir une seule feature
2. choisir un seul profil de test
3. executer le scenario
4. noter le resultat
5. si bug : documenter et ne pas melanger avec 4 autres problemes
6. passer au scenario suivant

Le meilleur rythme est :

- 1 session de recette `pre-challenge`
- 1 session `Jour 1`
- 1 session `Jour 2`
- 1 session `Jour 3`
- 1 session `post-live / objections / dashboard`

---

## 11. Validation finale

La plateforme est consideree testable proprement si :

- chaque feature peut etre testee de facon isolee
- chaque resultat attendu est observable
- chaque bug peut etre relie a un scenario clair
- chaque retour peut etre reutilise pour correction sans ambiguite

Ce runbook doit devenir ton support de recette principal pour verifier la plateforme et me faire des retours exploitables rapidement.

