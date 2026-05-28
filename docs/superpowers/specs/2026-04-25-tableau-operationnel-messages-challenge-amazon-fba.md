# Tableau operationnel detaille - Messages et automatisations du Challenge Amazon FBA

**Date :** 2026-04-25  
**Objet :** cadrer message par message les automatisations WhatsApp du `Challenge Amazon FBA` avant configuration.  
**Perimetre :** pre-challenge, Jour 1, Jour 2, Jour 3, post-challenge, FAQ, objections et reprises humaines.

---

## 1. Regles generales

- chaque message est attache a une `edition` du challenge
- chaque contact appartient a une cohorte `EU` ou `US-CA`
- les liens `StreamYard` sont propres a chaque edition
- les cohortes viennent de `deux listes Systeme.io distinctes`
- les messages doivent pouvoir varier selon le segment : `froid`, `tiede`, `chaud`, `tres_chaud`
- les objections se traitent surtout en `post-live`

### Definition rapide des segments

- `froid` : inscrit mais peu reactif
- `tiede` : ouvre ou lit, mais reste peu engage
- `chaud` : clique, rejoint un live, pose des questions
- `tres_chaud` : participe, manifeste une intention commerciale ou demande des precisions sur l'offre

---

## 2. Tableau operationnel

| ID | Moment d'envoi | Cohorte | Declencheur | Objectif | Variante segment | Fallback si non-reponse | Escalade eventuelle |
|---|---|---|---|---|---|---|---|
| M01 | immediat apres inscription | EU + US-CA | `lead_captured` depuis Systeme.io | souhaiter la bienvenue et confirmer l'entree dans le challenge | `froid/tiede` : ton simple et rassurant, `chaud/tres_chaud` : ton plus direct | renvoyer `M02` si pas d'ouverture / pas d'interaction dans les 6h | non |
| M02 | immediat apres M01 | EU + US-CA | inscription validee | confirmer la cohorte, le rythme du challenge et le fait que les infos seront aussi envoyees par email | `froid` : tres pedagogique, `chaud` : focus sur le live | reenvoyer rappel horaire la veille ou le matin du Jour 1 | non |
| M03 | immediat apres M02 | EU + US-CA | inscription validee | expliquer comment rejoindre le groupe WhatsApp | `froid` : etapes simples, `tiede/chaud` : format plus court | si pas de clic / question sur groupe, envoyer FAQ groupe | oui si la personne ne parvient pas a rejoindre le groupe apres 2 tentatives |
| M04 | immediat apres M02 | EU + US-CA | inscription validee | rappeler que les liens live seront envoyes par email puis dans les groupes pendant le challenge | tous segments : message standard | si la personne dit ne pas avoir recu d'email, basculer sur FAQ email | oui si probleme technique repete |
| M05 | veille du Jour 1 au soir ou Jour 1 matin | EU | contact assigne a une edition EU | rappeler que le challenge commence a `21h00 Europe` | `froid` : rassurer, `chaud` : insister sur presence | renvoyer version courte a H-6 si aucune action | non |
| M06 | veille du Jour 1 au soir ou Jour 1 matin | US-CA | contact assigne a une edition US-CA | rappeler que le challenge commence a `19h00 Montreal / New York` | idem M05 | renvoyer version courte a H-6 si aucune action | non |
| M07 | Jour 1 H-6 | EU + US-CA | live du Jour 1 prevu | preparer mentalement la presence au live | `froid` : rappeler la promesse, `chaud` : appeler a etre present | si pas de clic, envoyer `M08` puis `M09` | non |
| M08 | Jour 1 H-45 min | EU + US-CA | lien StreamYard disponible | livrer le lien du live du Jour 1 | `froid` : format simple, `chaud` : ton plus dynamique | si pas de clic, envoyer `M09` | non |
| M09 | Jour 1 H-10 min | EU + US-CA | pas de clic sur le lien du Jour 1 | faire une derniere relance courte avant le live | `froid` : "il est encore temps", `chaud` : "on commence dans quelques minutes" | si non-presence, envoyer `M10` | non |
| M10 | Jour 1 +2h | EU + US-CA | live Jour 1 termine | envoyer recap ou rattrapage | `chaud/tres_chaud` : recap + suite, `froid/tiede` : resume simple | si pas de reaction, envoyer reengagement Jour 2 | non |
| M11 | Jour 1 +6h | EU + US-CA | objection entendue en live ou pricing question detectee | faire un premier suivi post-pitch | `chaud` : reponse budget, `tres_chaud` : proposer echange ou precision | si aucune suite, envoyer suivi Jour 2 adapte | oui si demande d'appel ou demande commerciale explicite |
| M12 | Jour 2 H-6 | EU + US-CA | live Jour 2 prevu | remobiliser pour le Jour 2 | `froid` : "reprendre le fil", `chaud` : "continuer le challenge" | si aucun clic, envoyer lien puis relance courte | non |
| M13 | Jour 2 H-45 min | EU + US-CA | lien StreamYard du Jour 2 disponible | envoyer lien du Jour 2 | tous segments : standard | si pas de clic, envoyer `M14` | non |
| M14 | Jour 2 H-10 min | EU + US-CA | pas de clic Jour 2 | derniere relance avant demarrage | `froid` : insister sur valeur, `chaud` : ton direct | si absence, envoyer `M15` | non |
| M15 | Jour 2 +2h | EU + US-CA | live Jour 2 termine | recap ou rattrapage Jour 2 | `tiede` : remise en contexte, `chaud` : suite logique | si a manque Jour 1 et 2, brancher relance de recuperation | non |
| M16 | Jour 2 +6h | EU + US-CA | demande de paiement en plusieurs fois | traiter le besoin de plan de paiement | `tres_chaud` : suivi prioritaire, `chaud` : reponse informative | si pas de suite, creer file de suivi humain | oui, priorite haute |
| M17 | Jour 2 +6h | EU + US-CA | tentative paiement echouee / fonds insuffisants | ne pas laisser tomber un acheteur potentiel | tous segments : ton empathique | si aucune suite, relance humaine sous 24h | oui, priorite haute |
| M18 | Jour 3 H-6 | EU + US-CA | live final prevu | maximiser la presence au dernier jour | `froid` : "ne ratez pas la fin", `tres_chaud` : appel fort a etre la | si pas de clic, envoyer `M19` | non |
| M19 | Jour 3 H-45 min | EU + US-CA | lien StreamYard Jour 3 disponible | envoyer lien du live final | standard | si pas de clic, envoyer `M20` | non |
| M20 | Jour 3 H-10 min | EU + US-CA | pas de clic Jour 3 | dernier rappel avant session finale | `chaud/tres_chaud` : plus direct | si absence, envoyer `M21` | non |
| M21 | Jour 3 +3h | EU + US-CA | fin du challenge | suivi post-challenge oriente offre / prochaine etape | `froid/tiede` : recap + valeur, `chaud/tres_chaud` : CTA plus fort | si pas de reponse, envoyer objection ou next challenge selon signal | oui si contact tres chaud silencieux |
| M22 | Jour 3 +6h a J+1 | EU + US-CA | objection budget detectee | repondre au frein financier sans casser l'envie | `soft` : rassurer, `strong` : clarifier et orienter | si aucune suite, file manuelle si lead engage | oui si lead chaud ou tres chaud |
| M23 | Jour 3 +6h a J+1 | EU + US-CA | scepticisme / peur de perdre son argent | traiter l'objection de confiance | `tiede` : rassurance simple, `chaud/tres_chaud` : elements de confiance plus concrets | si pas de reponse, proposer reprise humaine | oui, priorite moyenne |
| M24 | J+1 | EU + US-CA | "je reviendrai plus tard" ou "je le ferai les jours suivants" | transformer le report en action concrete | `chaud` : relance action, `tres_chaud` : suivi rapproche | si aucune suite, reclasser en tiede et reprogrammer | oui si signaux d'achat forts |
| M25 | J+1 | EU + US-CA | demande "quand est-ce que vous referez un nouveau challenge ?" | capter l'interet pour une prochaine edition | `froid/tiede` : orientation simple, `chaud` : garder dans pipeline | si aucune suite, stocker pour relance sur prochaine edition | non |
| M26 | a tout moment | EU + US-CA | `faq_whatsapp_group_join` | repondre a la question groupe WhatsApp | tous segments : reponse courte | si la personne bloque encore, file support | oui si echec repete |
| M27 | a tout moment | EU + US-CA | `faq_email_missing` | gerer "je me suis inscrit mais je n'ai pas recu d'email" | tous segments : verifier spam + groupe | si probleme persiste, reprise manuelle | oui |
| M28 | a tout moment | EU + US-CA | `faq_start_time` | rappeler quand cela commence selon cohorte | `EU` : 21h Europe, `US-CA` : 19h Montreal/New York | si question reste floue, renvoyer recap cohorte | non |
| M29 | a tout moment | EU + US-CA | `faq_offer_price` | clarifier que le challenge est gratuit et que l'offre est expliquee pendant/apres | `froid` : rassurer, `chaud` : orienter vers suite | si devient objection financiere, basculer `M22` | oui si lead tres chaud |
| M30 | a tout moment | EU + US-CA | `faq_next_challenge_date` | repondre sur la prochaine edition | tous segments : info simple + capture interet | si le lead est engage, le tagger pour relance future | non |

---

## 3. Regles de fallback

### Non-reponse simple

- si un message critique n'obtient aucune interaction : relance courte 1 fois
- si aucune interaction apres 2 tentatives : bascule sur branche comportementale `inactive_registered`

### Non-clic sur lien live

- relance courte a `H-10`
- si toujours pas de clic : message post-live de rattrapage

### Absence au live

- envoyer recap/rattrapage
- reengager sur le jour suivant
- si absences repetees : segment tiede ou froid selon signaux annexes

### Silence apres objection

- si objection budgetaire et lead peu engage : relance douce
- si objection budgetaire et lead chaud/tres chaud : file manuelle

---

## 4. Regles d'escalade humaine

Escalade `haute priorite` :

- tentative de paiement echouee
- demande explicite de plan de paiement
- lead tres chaud avec objection financiere
- demande d'appel ou de reprise commerciale

Escalade `priorite moyenne` :

- scepticisme apres participation au live
- probleme email persistant
- demande repetitive sans resolution

Escalade `priorite faible` :

- FAQ simples sans signal commercial
- demande de prochaine date sans autre engagement

---

## 5. Evenements a tracer par message

Pour chaque message, tracer si possible :

- `sent`
- `delivered`
- `opened` si disponible
- `clicked`
- `replied`
- `faq_detected`
- `objection_detected`
- `human_escalation_required`

Pour les messages commerciaux, tracer aussi :

- `pricing_question_detected`
- `installment_plan_requested`
- `payment_failed_insufficient_funds`
- `next_challenge_requested`
- `skepticism_detected`

---

## 6. Priorites de configuration

Ordre recommande :

1. `M01` a `M10` : colonne vertebrale pre-challenge + Jour 1
2. `M12` a `M21` : Jour 2, Jour 3 et post-challenge
3. `M26` a `M30` : FAQ bornees
4. `M22` a `M25` : objections, plans de paiement, scepticisme, prochaine edition
5. escalades et dashboard de suivi

---

## 7. Validation attendue avant configuration

Avant mise en place, il faudra valider :

- wording exact de chaque message
- ton par cohorte si necessaire
- presence ou non d'une difference de copy entre `EU` et `US-CA`
- regles de priorite commerciale
- traitement exact des plans de paiement
- traitement exact des paiements echoues
- mecanisme de recontact pour prochaine edition
