# SkillOpt - bot WhatsApp Challenge Amazon FBA

Ce dossier prepare l'utilisation de Microsoft SkillOpt pour ameliorer le bot
WhatsApp a partir d'exemples reels.

SkillOpt n'est pas un fine-tuning du modele. Le principe est de faire evoluer
un fichier de competence en langage naturel, puis d'accepter les modifications
uniquement si elles ameliorent un jeu de validation.

Sources utilisees :
- conversations exportees Wati du 28/05/2026 ;
- incidents observes : boucles de clarification, confusion sur les liens,
  fuseau horaire Haiti/Montreal, confirmations de presence, debutants sans
  question precise.

## Artefacts

- `bot_reply_skill.md` : competence initiale a optimiser.
- `split/train/items.json` : exemples d'apprentissage.
- `split/val/items.json` : exemples de validation.
- `split/test/items.json` : exemples de non-regression.

## Methode recommandee

1. Ajouter les conversations reelles ratees dans `split/train`.
2. Garder au moins 30 % des cas dans `split/val` et `split/test`.
3. Lancer SkillOpt sur un environnement QA ou adapter un benchmark custom.
4. Relire le `best_skill.md` obtenu.
5. Transformer seulement les regles stables en code ou knowledge base.
6. Ajouter un test e2e avant de deployer.

Ne jamais remplacer directement la logique de production par une sortie SkillOpt
non relue. Le bot WhatsApp doit rester court, prudent et testable.
