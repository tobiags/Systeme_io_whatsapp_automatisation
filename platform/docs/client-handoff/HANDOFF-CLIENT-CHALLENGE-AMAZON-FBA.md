# Document de Remise Client - Challenge Amazon FBA (Automatisation WhatsApp)

## 1. Objet du document

Ce document est le document de remise client du système d'automatisation WhatsApp construit pour le Challenge Amazon FBA.

Il explique :

- ce qui a été livré
- comment utiliser le système de bout en bout
- quels liens et outils doivent être utilisés
- quoi faire avant, pendant et après chaque live
- comment vérifier que tout fonctionne
- quelles sont les possibilités d'évolution et de scaling du système

---

## 2. Ce qui a été livré

### 2.1 Résultat métier

- Les leads sont captés depuis les funnels Systeme.io et injectés dans la plateforme.
- Les contacts sont enrôlés automatiquement dans la bonne cohorte (`EU` ou `US-CA`).
- Les messages WhatsApp sont envoyés via Wati avec les templates approuvés.
- Les signaux StreamYard (inscrits / présents) pilotent les branches de relance Jour 2, Jour 3 et post-live.
- Les envois s'arrêtent automatiquement après détection d'un achat.
- Un portail opérateur `PILOTAGE LIVE` permet d'exécuter le workflow live sans SSH, sans Termius et sans commande `curl`.

### 2.2 Composants principaux

- WhatsApp Business / envoi des messages : Wati
- Source des leads : Systeme.io
- Orchestration : n8n
- Services plateforme : API, scheduler, scoring, consentement, logique campagne
- Interface opérateur :
  - Console Admin
  - Portail StreamYard `PILOTAGE LIVE`

---

## 3. Définitions utiles

- **Cohorte**
  - `EU`
  - `US-CA`

- **Edition key**
  - identifiant unique d'une édition du challenge
  - exemple : `2026-05-21-usca`

- **Jour**
  - `1`, `2`, `3`
  - correspond aux 3 sessions live du challenge

- **Template Wati**
  - message WhatsApp validé avec variables `{{1}}`, `{{2}}`, `{{3}}`, `{{4}}`

- **PILOTAGE LIVE**
  - page opérateur utilisée pour :
    - enregistrer le lien StreamYard du jour
    - enregistrer les liens variables de l'édition
    - envoyer les inscrits StreamYard
    - envoyer les présents StreamYard

---

## 4. Liens et accès à utiliser

### 4.1 Console Admin

- URL : `http://whatsapp.178.104.229.163.nip.io:3001/`

Utilité :
- voir l'état général de la plateforme
- suivre les contacts
- suivre les messages envoyés
- suivre les relances humaines

### 4.2 Portail StreamYard - PILOTAGE LIVE

- URL : `http://whatsapp.178.104.229.163.nip.io:3001/ops/streamyard?token=ops_streamyard_2026_fba_client_x9K4mP2qL7zR`

Important :
- ce lien doit rester privé
- il donne accès à l'outil opérateur du challenge

### 4.3 Wati

À confirmer côté client :
- nom du workspace Wati
- numéro WhatsApp Business connecté

Utilité :
- recevoir les réponses des leads
- répondre manuellement si nécessaire
- surveiller les conversations et notifications

---

## 5. Liens variables à renseigner pour chaque édition

Ces liens ne sont pas stockés comme une configuration fixe globale.

Ils sont maintenant gérés **par édition**, directement depuis `PILOTAGE LIVE`.

### 5.1 Liens à prévoir

- lien de paiement de l'offre Jour 3
- lien de réservation / closer
- lien replay Jour 1
- lien replay Jour 2
- lien replay Jour 3

### 5.2 Où ces liens sont utilisés

- **Lien paiement**
  - utilisé dans le template `live_day3_offer_hplus2`

- **Lien closer / réservation**
  - utilisé dans :
    - `post_closer_call`
    - `post_recap_attended`

- **Liens replay**
  - utilisés dans :
    - `post_recap_registered_absent`
    - `post_recap_not_registered`

### 5.3 Règle importante

Ces liens doivent être renseignés pour **chaque nouvelle édition** si :

- l'offre change
- le lien closer change
- les liens replay changent

---

## 6. Templates Wati attendus

Le système a été aligné sur les templates Wati validés / prévus, notamment :

- `welcome`
- `countdown_j6` à `countdown_j1`
- `live_day1`
- `live_day1_h10`
- `live_day1_hplus5`
- `live_day2_attended_v2`
- `live_day2_registered_absent`
- `live_day2_not_registered`
- `live_day2_h10`
- `live_day2_hplus5`
- `live_day3_attended_v2`
- `live_day3_registered_absent`
- `live_day3_not_registered`
- `live_day3_h10`
- `live_day3_hplus5`
- `live_day3_offer_hplus2`
- `post_recap_attended`
- `post_recap_registered_absent`
- `post_recap_not_registered`
- `post_inaction_reason`
- `post_closer_call`

Remarque :
- `post_testimonials` reste optionnel selon disponibilité du contenu réel

---

## 7. Procédure d'utilisation complète

Cette partie est écrite pour permettre une utilisation autonome, sans intervention technique.

### Etape 1 - Vérifier Wati

Avant de lancer une édition :

1. Ouvrir Wati
2. Vérifier que le numéro WhatsApp Business est bien connecté
3. Vérifier que les templates nécessaires sont approuvés
4. Vérifier que l'inbox Wati est accessible

Vérification conseillée :
- envoyer un test manuel sur un numéro de test

### Etape 2 - Vérifier Systeme.io

Pour chaque funnel actif :

1. Ouvrir le funnel Systeme.io
2. Aller sur la page d'opt-in
3. Vérifier que la règle d'automatisation webhook existe bien

Funnels concernés :
- funnel EU
- funnel US/CA

Effet attendu :
- à chaque inscription, le contact est créé dans la plateforme
- le `welcome` est envoyé automatiquement

### Etape 3 - Préparer les lives StreamYard

Pour chaque cohorte et chaque jour :

1. créer ou vérifier le live StreamYard
2. récupérer le lien du live
3. préparer la liste des inscrits
4. après le live, préparer la liste des présents

---

## 8. Utilisation du portail PILOTAGE LIVE

### 8.1 Avant le live - enregistrer le lien du jour

À faire pour chaque cohorte et chaque jour.

1. Ouvrir `PILOTAGE LIVE`
2. Choisir la cohorte
3. Renseigner `edition_key`
4. Choisir le jour (`1`, `2` ou `3`)
5. Coller le lien StreamYard du jour
6. Cliquer sur **Enregistrer le live**

Effet :
- les rappels live utiliseront le bon lien StreamYard

### 8.2 Avant l'offre et le post-live - enregistrer les liens variables

À faire une fois par édition, puis à mettre à jour si les liens changent.

1. Rester sur `PILOTAGE LIVE`
2. Garder la bonne cohorte et la bonne `edition_key`
3. Renseigner :
   - lien paiement
   - lien closer / réservation
   - replay Jour 1
   - replay Jour 2
   - replay Jour 3
4. Cliquer sur **Enregistrer les liens**

Effet :
- les messages d'offre Jour 3 utilisent le bon lien paiement
- les messages post-live utilisent les bons replays
- les messages closer utilisent le bon lien de réservation

### 8.3 Juste avant le live - envoyer les inscrits

1. Exporter ou récupérer les inscrits StreamYard
2. Les coller dans la zone prévue ou importer un CSV
3. Cliquer sur **Envoyer les inscrits**

Effet :
- le système saura distinguer :
  - les inscrits absents
  - les non inscrits

### 8.4 Après le live - envoyer les présents

1. Exporter ou récupérer les présents
2. Les coller dans la zone prévue ou importer un CSV
3. Cliquer sur **Envoyer les présents**

Effet :
- le système saura distinguer :
  - les présents
  - les inscrits absents
  - les non inscrits

Cela permet d'envoyer la bonne relance au bon contact.

---

## 9. Vérifications recommandées

### 9.1 Vérification simple à faire avant une vraie édition

1. Faire une inscription test sur le funnel
2. Vérifier :
   - création du contact
   - enrôlement
   - envoi du `welcome`
3. Tester `PILOTAGE LIVE` avec :
   - un lien StreamYard
   - des inscrits
   - des présents

### 9.2 Vérification pendant l'exploitation

Surveiller :
- Wati Inbox
- Console Admin
- nombre de messages envoyés
- file de relances humaines

---

## 10. Que faire si quelque chose semble incorrect

### Message WhatsApp non envoyé

Vérifier :

1. que Wati est bien connecté
2. que le template existe et est approuvé
3. que le contact a bien donné son consentement
4. que le bon lien live a bien été enregistré pour le bon jour

### Mauvais lien dans un message live

1. Ouvrir `PILOTAGE LIVE`
2. vérifier la cohorte
3. vérifier l'`edition_key`
4. réenregistrer le lien StreamYard du jour

### Mauvais lien closer / paiement / replay

1. Ouvrir `PILOTAGE LIVE`
2. vérifier la bonne `edition_key`
3. corriger le ou les liens dans la section dédiée
4. recliquer sur **Enregistrer les liens**

### Mauvaise branche présent / absent / non inscrit

Vérifier :

1. que les inscrits ont bien été envoyés
2. que les présents ont bien été envoyés après le live

---

## 11. Ce qui a été réalisé techniquement

Le projet livré inclut :

- intégration Systeme.io
- intégration n8n
- intégration Wati
- gestion du consentement
- scoring et segmentation
- logique de branches comportementales
- arrêt automatique des envois après achat
- portail opérateur StreamYard
- console admin
- documentation de remise

En résumé :
- le socle technique est construit
- l'exploitation est cadrée
- le client peut travailler sans passer par des commandes serveur

---

## 12. Avantages concrets pour le client

### 12.1 Gain opérationnel

- plus besoin de manipulations techniques pour les lives
- moins d'erreurs humaines
- processus clair et reproductible

### 12.2 Gain commercial

- meilleur suivi des leads
- relances plus pertinentes
- meilleure attendance live
- meilleure qualité de reprise post-live

### 12.3 Gain de lisibilité

- visibilité centralisée dans la console
- inbox Wati pour les réponses
- logique de cohortes plus propre

---

## 13. Limites connues et règle d'exploitation

Le système est automatisé, mais la partie StreamYard reste volontairement opérateur.

Concrètement :

- le client doit encore renseigner les éléments live dans `PILOTAGE LIVE`
- cette procédure existe parce que StreamYard ne fournit pas ici une intégration exploitable aussi simplement que Systeme.io

Cela reste une procédure légère, mais elle doit être faite sérieusement à chaque édition.

---

## 14. Possibilités de scaling du système

Le système actuel peut déjà produire des résultats.

Mais il peut aussi être développé dans une logique de retainer pour augmenter la performance commerciale, réduire l'effort humain et professionnaliser encore davantage l'exploitation.

### Option A - Optimisation conversion continue

Ce qui peut être ajouté :

- amélioration mensuelle des séquences
- optimisation des timings de relance
- A/B tests sur messages et transitions
- amélioration des branches comportementales

Bénéfice :
- plus de présence live
- meilleure conversion sans augmenter le budget pub

### Option B - Réduction de l'effort opérateur

Ce qui peut être ajouté :

- rappels intelligents si l'équipe oublie une étape StreamYard
- contrôle qualité automatique
- semi-automatisation plus poussée autour des exports

Bénéfice :
- moins de risque d'erreur
- moins de dépendance à une personne précise

### Option C - Amélioration du suivi commercial

Ce qui peut être ajouté :

- meilleure vue closer
- priorisation automatique des leads chauds
- suivi avancé des objections
- enrichissement de la relance humaine

Bénéfice :
- meilleure efficacité commerciale
- meilleur taux de closing

### Option D - Intelligence conversationnelle plus avancée

Ce qui peut être ajouté :

- mémoire plus riche par lead
- handoff plus propre entre IA et humain
- détection d'intention plus fine
- scénarios de reprise personnalisés

Bénéfice :
- meilleure expérience prospect
- plus de confiance
- plus de cohérence sur toute la durée du challenge

---

## 15. Conclusion

Le système livré permet :

- de capter les leads
- de les faire entrer dans la bonne cohorte
- de les relancer automatiquement sur WhatsApp
- de piloter correctement les sessions live
- de distinguer présents, absents et non inscrits
- de reprendre les leads après le challenge

Le client dispose maintenant :

- d'un système fonctionnel
- d'un portail opérateur simple
- d'une procédure claire
- d'une base solide qui peut évoluer vers un accompagnement mensuel plus stratégique

---

## 16. Checklist finale d'utilisation

Avant une édition :

- vérifier Wati
- vérifier Systeme.io
- créer les lives StreamYard
- ouvrir `PILOTAGE LIVE`
- enregistrer les liens live
- enregistrer les liens variables de l'édition

Pendant l'édition :

- envoyer les inscrits
- envoyer les présents
- surveiller Wati et la console admin

Après l'édition :

- vérifier les replays
- vérifier les relances post-live
- suivre les réponses humaines et les closers
