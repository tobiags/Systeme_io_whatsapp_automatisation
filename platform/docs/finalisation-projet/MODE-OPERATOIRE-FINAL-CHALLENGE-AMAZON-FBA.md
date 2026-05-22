# Mode Operatoire Final - Challenge Amazon FBA

## Objet du document

Ce document explique comment utiliser le systeme en autonomie pour gerer le challenge Amazon FBA, sans intervention technique.

Le systeme automatise :

- la capture des leads depuis Systeme.io
- la creation des contacts
- l'enrolement dans la bonne cohorte
- l'envoi des messages WhatsApp via Wati
- les relances selon le parcours
- l'arret automatique des messages apres achat

La seule partie qui reste operateur autour des lives est StreamYard, via une page simple de pilotage.

---

## Outils utilises

### 1. Systeme.io

Systeme.io sert a capter les inscriptions depuis les funnels.

Cette partie est deja branchee.  
Une nouvelle inscription cree automatiquement le contact dans la plateforme et declenche le premier message WhatsApp.

### 2. Wati

Wati sert a :

- envoyer les messages WhatsApp
- recevoir les reponses des leads
- repondre manuellement si besoin
- recevoir les notifications de nouvelles reponses

### 3. Portail "PILOTAGE LIVE"

Le portail "PILOTAGE LIVE" sert a alimenter le systeme avec les donnees StreamYard :

- lien du live du jour
- inscrits StreamYard
- presents au live

Cette page remplace les manipulations Termius et les commandes curl.

---

## Acces utiles

### Inbox Wati

Les reponses des leads se lisent et se traitent dans Wati.

### Application mobile Wati

Il est recommande d'installer l'application mobile Wati et d'activer les notifications pour etre averti des reponses sans surveiller le dashboard en permanence.

### Portail PILOTAGE LIVE

Le portail de pilotage est accessible via le lien direct transmis lors de la mise en service.

Ce lien contient deja le token d'acces.  
Il peut etre ouvert depuis un ordinateur ou un telephone.

---

## Fonctionnement general

### Ce qui est automatique

- inscription via Systeme.io
- creation du contact
- affectation a la cohorte EU ou US-CA
- envoi du message de bienvenue
- poursuite de la sequence WhatsApp
- arret des relances si la personne achete

### Ce qui est manuel

Avant, pendant et apres chaque live, il faut utiliser le portail "PILOTAGE LIVE" pour renseigner les donnees StreamYard.

Sans cette etape, le systeme ne peut pas savoir :

- quel lien de live envoyer
- qui s'est inscrit au live
- qui etait present en direct

---

## Procedure complete a chaque live

## Etape 1 - Avant le live

Objectif : enregistrer le lien StreamYard du jour.

### A faire

1. Ouvrir le portail "PILOTAGE LIVE"
2. Renseigner :
   - la cohorte : `EU` ou `US/CA`
   - l'edition key
   - le jour : `Jour 1`, `Jour 2` ou `Jour 3`
   - le lien StreamYard du live
3. Cliquer sur `Enregistrer le live`

### Resultat attendu

Un message de confirmation s'affiche.  
Les rappels utiliseront ensuite ce lien.

### Important

Cette action est a faire une seule fois par cohorte et par jour.

---

## Etape 2 - Juste avant / au debut du live

Objectif : indiquer au systeme qui s'est inscrit au live StreamYard.

### A faire

1. Recuperer la liste des inscrits StreamYard
2. Ouvrir la section `2. Juste avant / au debut`
3. Choisir l'une des deux methodes :
   - coller les numeros dans le champ prevu
   - importer le fichier CSV StreamYard
4. Cliquer sur `Envoyer les inscrits`

### Resultat attendu

Le portail affiche un retour du type :

- `X inscrit(s) enregistres`
- `Y deja connus`
- `Z non trouves`

### Recommandation

Si les numeros sont disponibles rapidement, la methode la plus simple est de les coller directement dans le champ.

---

## Etape 3 - Apres le live

Objectif : indiquer au systeme qui a effectivement assiste au live.

### A faire

1. Recuperer la liste des presents au live
2. Ouvrir la section `3. Apres le live`
3. Choisir l'une des deux methodes :
   - coller les numeros
   - importer le CSV
4. Cliquer sur `Envoyer les presents`

### Resultat attendu

Le portail affiche un retour du type :

- `X present(s) enregistres`
- `Y deja connus`
- `Z non trouves`

### Pourquoi cette etape est importante

C'est cette information qui permet au systeme d'envoyer les bonnes relances :

- presents
- inscrits absents
- non inscrits

---

## Que faire dans Wati

## Voir les reponses

Les reponses des leads arrivent dans l'inbox Wati.

Il suffit d'ouvrir Wati pour :

- lire les reponses
- reprendre une conversation
- repondre manuellement si besoin

## Notifications

Il est recommande :

1. d'activer les notifications Wati sur ordinateur
2. d'installer l'application mobile Wati
3. d'activer les notifications push sur mobile

De cette facon, il n'est pas necessaire de rester connecte en permanence au dashboard web.

---

## Checklist simple avant un live

- verifier que le bon funnel Systeme.io est actif
- verifier que le numero WhatsApp Wati est connecte
- ouvrir le portail `PILOTAGE LIVE`
- renseigner le lien du live
- verifier le message de succes

---

## Checklist simple au debut du live

- recuperer les inscrits StreamYard
- les coller ou importer le CSV
- cliquer sur `Envoyer les inscrits`
- verifier le message de succes

---

## Checklist simple apres le live

- recuperer la liste des presents
- les coller ou importer le CSV
- cliquer sur `Envoyer les presents`
- verifier le message de succes

---

## Erreurs a eviter

- ne pas oublier d'enregistrer le lien du live avant les rappels
- ne pas melanger les cohortes EU et US-CA
- ne pas envoyer les presents dans la section des inscrits
- ne pas partager le lien du portail avec des personnes non autorisees
- ne pas modifier les webhooks ou secrets sans verification

---

## Si un message ne part pas

Verifier dans cet ordre :

1. que le numero Wati est bien connecte
2. que le template Wati correspondant existe et est approuve
3. que le lien du live a bien ete enregistre dans `PILOTAGE LIVE`
4. que la personne est bien entree dans le systeme via Systeme.io

---

## Si une reponse lead n'apparait pas

Verifier :

1. l'inbox Wati
2. les notifications Wati
3. que la conversation a bien ete recue sur le numero connecte

---

## Si une manipulation StreamYard a ete oubliee

La regle est simple :

- si le lien du live n'a pas ete renseigne, l'enregistrer des que possible
- si les inscrits n'ont pas ete envoyes, les envoyer des que la liste est disponible
- si les presents n'ont pas ete envoyes, les envoyer apres recuperation de la liste

Le systeme reste exploitable, mais la qualite des relances depend de cette discipline operatoire.

---

## Ce qui est deja en place dans le projet

- capture automatique des leads Systeme.io
- creation automatique des contacts
- enrolement automatique campagne
- message `welcome` envoye automatiquement
- sequence WhatsApp validee
- portail de pilotage StreamYard
- gestion des cohortes
- arret automatique apres achat

---

## Conclusion

Le systeme est desormais exploitable sans intervention technique quotidienne.

Le fonctionnement normal est le suivant :

1. les leads entrent automatiquement via Systeme.io
2. les messages WhatsApp partent automatiquement
3. les reponses se lisent dans Wati
4. les lives sont pilotes via la page `PILOTAGE LIVE`

L'essentiel pour bien faire tourner le systeme est donc :

- surveiller Wati pour les reponses
- utiliser correctement le portail avant et apres chaque live
- respecter la bonne cohorte et le bon jour
