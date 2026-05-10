const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
} = require('docx');
const fs = require('fs');
const path = require('path');

// ─── PALETTE ──────────────────────────────────────────────────────────────────
const C = {
  primary:    '1D4ED8', primaryDk: '1E3A8A',
  green:      '059669', greenBg:   'ECFDF5', greenDk: '065F46',
  purple:     '7C3AED', purpleBg:  'EDE9FE',
  amber:      'D97706', amberBg:   'FEF3C7',
  red:        'DC2626', redBg:     'FEF2F2',
  blue:       '0284C7', blueBg:    'EFF6FF',
  gray50:     'F8FAFC', gray200:   'E2E8F0',
  gray400:    '94A3B8', gray700:   '334155',
  white:      'FFFFFF', black:     '0F172A',
};

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const cb = (color = C.gray200) => ({
  top:    { style: BorderStyle.SINGLE, size: 1, color },
  bottom: { style: BorderStyle.SINGLE, size: 1, color },
  left:   { style: BorderStyle.SINGLE, size: 1, color },
  right:  { style: BorderStyle.SINGLE, size: 1, color },
});
const thickLeft = (color) => ({
  top:    { style: BorderStyle.SINGLE, size: 2, color },
  bottom: { style: BorderStyle.SINGLE, size: 2, color },
  left:   { style: BorderStyle.THICK,  size: 12, color },
  right:  { style: BorderStyle.SINGLE, size: 2, color },
});

const r  = (text, opts = {}) => new TextRun({ text, font: 'Arial', ...opts });
const br = (text, opts = {}) => r(text, { bold: true, ...opts });
const sp = (n = 1) => Array.from({ length: n }, () =>
  new Paragraph({ children: [r('')] }));

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [br(text, { size: 30, color: C.primaryDk })],
    spacing: { before: 360, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.primary, space: 4 } },
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [br(text, { size: 24, color: C.primary })],
    spacing: { before: 240, after: 100 },
  });
}
function h3(text, color = C.gray700) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [br(text, { size: 20, color })],
    spacing: { before: 180, after: 80 },
  });
}
function body(text, opts = {}) {
  return new Paragraph({ children: [r(text, { size: 20, ...opts })], spacing: { before: 60, after: 60 } });
}

function banner(lines, bgColor, borderColor, icon = '') {
  const children = lines.map((line, i) =>
    new Paragraph({
      children: [r(i === 0 && icon ? icon + '  ' : '', { bold: true, size: 18, color: borderColor }),
                 r(line, { size: 18, color: i === 0 ? borderColor : C.gray700, bold: i === 0 })],
      spacing: { before: i === 0 ? 0 : 60, after: 0 },
    })
  );
  return new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: 9360, type: WidthType.DXA },
      borders: thickLeft(borderColor),
      shading: { type: ShadingType.CLEAR, fill: bgColor },
      margins: { top: 100, bottom: 100, left: 200, right: 200 },
      children,
    })] })],
  });
}

function msgBox(lines) {
  const children = lines.map((line, i) => {
    const parts = line.split(/({{[^}]+}})/g);
    const runs = parts.map(p =>
      /^{{[^}]+}}$/.test(p)
        ? r(p, { bold: true, color: C.green, size: 20 })
        : r(p, { size: 20, color: C.black })
    );
    return new Paragraph({ children: runs, spacing: { before: i === 0 ? 0 : 60, after: 0 } });
  });
  return new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: 9360, type: WidthType.DXA },
      borders: thickLeft(C.green),
      shading: { type: ShadingType.CLEAR, fill: C.greenBg },
      margins: { top: 120, bottom: 120, left: 220, right: 220 },
      children,
    })] })],
  });
}

function psychBox(lever, desc) {
  return banner([lever, desc], C.purpleBg, C.purple, '🧠');
}
function noteBox(lines) {
  return banner(lines, C.amberBg, C.amber, '⚙️');
}
function infoBox(lines) {
  return banner(lines, C.blueBg, C.blue, 'ℹ️');
}

function twoColTable(rows, w1 = 2400, w2 = 6960) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [w1, w2],
    rows: rows.map(([label, value], i) => new TableRow({ children: [
      new TableCell({
        width: { size: w1, type: WidthType.DXA },
        borders: cb(C.gray200),
        shading: { type: ShadingType.CLEAR, fill: C.gray50 },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [new Paragraph({ children: [br(label, { size: 18, color: C.primaryDk })] })],
      }),
      new TableCell({
        width: { size: w2, type: WidthType.DXA },
        borders: cb(C.gray200),
        shading: { type: ShadingType.CLEAR, fill: i % 2 === 0 ? C.white : C.gray50 },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [new Paragraph({ children: [r(value, { size: 18 })] })],
      }),
    ]})),
  });
}

// ─── TEMPLATE DATA ────────────────────────────────────────────────────────────

const PHASES = [

  // ═══════════════════════════════ PRÉ-CHALLENGE ═══════════════════════════════
  {
    phaseTitle: 'PHASE 1 — Pré-challenge (J-7 à J-1)',
    phaseColor: C.primary,
    phaseBg: C.blueBg,
    phaseDesc: 'Séquence de chauffe envoyée entre l\'inscription et le premier live. Un message par jour. Les inscrits tardifs démarrent au bon endroit selon leur date d\'inscription (voir logique d\'enrôlement intelligent, page 4).',
    templates: [
      {
        num: 1,
        key: 'welcome',
        name: 'Bienvenue — message immédiat à l\'inscription',
        timing: 'Immédiatement après l\'inscription (quelle que soit la date)',
        audience: 'Tous les inscrits — premier message reçu',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: 'Webhook Systeme.io → contact créé → message envoyé dans la minute',
        lever: 'Engagement & Cohérence (Commitment & Consistency)',
        psychDesc: 'Cialdini : le premier "oui" (inscription) crée une pression interne à rester cohérent. En posant une question ouverte dès le départ, on transforme le contact en interlocuteur actif plutôt que spectateur passif. La réponse à cette question alimente aussi l\'agent IA pour personnaliser les échanges suivants.',
        message: [
          'Bonjour {{1}} ! 👋',
          '',
          'Je suis ravi(e) de t\'accueillir dans le Challenge Amazon FBA !',
          '',
          'Dans les prochains jours, tu vas recevoir des infos et des ressources pour arriver préparé(e) aux 3 sessions live.',
          '',
          'Une chose m\'aiderait à mieux personnaliser ton expérience :',
          '',
          '❓ Qu\'est-ce qui t\'a poussé(e) à t\'inscrire ? Tu as déjà une idée de business, ou tu pars de zéro ?',
          '',
          'Réponds-moi ici — je lis tout 👇',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          'Pas de référence temporelle ("7 jours avant") — ce message est générique et fonctionne quelle que soit la date d\'inscription',
          'La réponse du contact est capturée par l\'agent IA (GPT-4o-mini) et apparaît dans la file de suivi',
          'Ce message remplace welcome_j7 — l\'ancien message avec "7 jours avant" est supprimé',
        ],
        placeholder: false,
      },
      {
        num: 2,
        key: 'countdown_j6',
        name: 'J-6 — Question sur leur situation actuelle',
        timing: 'J-6 avant le challenge (ou 24h après le welcome pour les inscriptions tardives)',
        audience: 'Tous les inscrits ayant reçu le welcome',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: 'Broadcast automatique J-6 ou 24h après welcome si inscription > J-6',
        lever: 'Effet Zeigarnik (boucle cognitive ouverte)',
        psychDesc: 'Une question ouverte crée une "boucle cognitive" non résolue : le cerveau ne peut pas l\'ignorer tant qu\'il n\'a pas répondu. Cela maintient le contact engagé psychologiquement entre les messages et augmente le taux d\'ouverture des suivants. La réponse reçue permet aussi de segmenter : débutant vs. déjà actif.',
        message: [
          'Bonjour {{1}} 👋',
          '',
          'J-6 avant le Challenge Amazon FBA — ça approche ! 🔥',
          '',
          'Une question rapide avant qu\'on commence :',
          '',
          '❓ Est-ce que tu vends déjà quelque chose en ligne, ou tu pars vraiment de zéro ?',
          '',
          'Ta réponse m\'aide à t\'envoyer les bons contenus de préparation.',
          '',
          'Réponds ici 👇',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          'Les réponses arrivent dans la file de l\'agent IA — prévoir de les lire et répondre',
          'Insight clé : la proportion débutants/avancés guide le ton des sessions live',
        ],
        placeholder: false,
      },
      {
        num: 3,
        key: 'countdown_j5',
        name: 'J-5 — Fait surprenant + curiosité',
        timing: 'J-5 avant le challenge',
        audience: 'Tous les inscrits',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: 'Broadcast automatique J-5',
        lever: 'Curiosity Gap + Mere Exposure Effect',
        psychDesc: 'Le "curiosity gap" (George Loewenstein) crée une tension entre ce qu\'on sait et ce qu\'on veut savoir. En révélant un fait contre-intuitif sur Amazon FBA, on génère l\'envie d\'en savoir plus. Le Mere Exposure Effect (familiarité = préférence) est aussi activé : chaque message quotidien renforce l\'attachement à la marque.',
        message: [
          '{{1}}, tu savais ça ? 🤔',
          '',
          'Des milliers de vendeurs Amazon ne voient, ne touchent et ne livrent jamais un seul produit.',
          '',
          'Amazon stocke tout dans ses entrepôts, emballe, expédie, et gère même le service client à leur place.',
          '',
          'C\'est le modèle FBA — et c\'est exactement ce qu\'on va décortiquer ensemble pendant le Challenge.',
          '',
          '❓ Selon toi, quel serait ton plus grand frein pour te lancer aujourd\'hui ?',
          '',
          'Dis-moi ici 👇',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          '[À PERSONNALISER] : remplacer le fait sur FBA par une stat ou anecdote réelle tirée de ton expérience',
          'La question finale est intentionnelle : elle prépare l\'agent IA à gérer les objections remontées',
        ],
        placeholder: true,
      },
      {
        num: 4,
        key: 'countdown_j4',
        name: 'J-4 — Social proof + communauté',
        timing: 'J-4 avant le challenge',
        audience: 'Tous les inscrits',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: 'Broadcast automatique J-4',
        lever: 'Preuve Sociale + Désir Mimétique (Mimetic Desire)',
        psychDesc: 'Girard / Cialdini : les gens veulent ce que les autres veulent. Montrer qu\'une communauté diverse de personnes (plusieurs pays, profils variés) s\'est inscrite active le désir mimétique. Le sentiment d\'appartenance à un groupe crée aussi un engagement émotionnel qui augmente le taux de présence aux sessions.',
        message: [
          'Bonjour {{1}} ! 👋',
          '',
          'On est maintenant [NOMBRE] personnes à se préparer pour le Challenge Amazon FBA.',
          '',
          'Ce qui est beau : certains viennent de France, d\'autres de Belgique, de Suisse, du Canada, du Maroc...',
          '',
          'Des profils très différents — salariés, entrepreneurs, étudiants — mais tous avec le même objectif : construire quelque chose qui travaille pour eux.',
          '',
          'Tu rejoins une vraie communauté. 🙌',
          '',
          'J-4 — hâte d\'être là ?',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          '[À PERSONNALISER] : remplacer [NOMBRE] par le nombre réel d\'inscrits — à mettre à jour avant chaque édition',
          'Ce message n\'a pas de question directe — c\'est volontaire pour varier les formats',
        ],
        placeholder: true,
      },
      {
        num: 5,
        key: 'countdown_j3',
        name: 'J-3 — Teaser du programme des 3 sessions',
        timing: 'J-3 avant le challenge',
        audience: 'Tous les inscrits',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: 'Broadcast automatique J-3',
        lever: 'Anticipation + Zeigarnik (boucles ouvertes)',
        psychDesc: 'Révéler le programme crée des boucles d\'anticipation pour chaque session. Le cerveau commence à "pré-traiter" les informations annoncées, ce qui augmente l\'engagement cognitif le jour J. La question "laquelle t\'excite le plus" force un choix qui crée un engagement supplémentaire.',
        message: [
          'J-3, {{1}} ! ⏰',
          '',
          'Voici ce qu\'on va voir ensemble pendant les 3 sessions live :',
          '',
          '👉 Session 1 : [RÉSUMÉ SESSION 1 — ex : "Comment fonctionne Amazon FBA de A à Z"]',
          '👉 Session 2 : [RÉSUMÉ SESSION 2 — ex : "Trouver et sourcer ton produit gagnant"]',
          '👉 Session 3 : [RÉSUMÉ SESSION 3 — ex : "Lancer, vendre et scaler sur Amazon"]',
          '',
          'Laquelle t\'excite le plus ? 🔥',
          '',
          'Réponds-moi ici 👇',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          '[À PERSONNALISER IMPÉRATIVEMENT] : remplacer les 3 résumés de sessions par le vrai contenu de tes lives StreamYard',
          'Ce message est l\'un des plus importants pour générer de l\'anticipation — soigne les titres des sessions',
        ],
        placeholder: true,
      },
      {
        num: 6,
        key: 'countdown_j2',
        name: 'J-2 — Logistique pratique',
        timing: 'J-2 avant le challenge',
        audience: 'Tous les inscrits',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: 'Broadcast automatique J-2',
        lever: 'Réduction de l\'Énergie d\'Activation (BJ Fogg Behavior Model)',
        psychDesc: 'BJ Fogg : un comportement se produit quand Motivation + Capacité + Déclencheur sont présents. Ce message réduit la "capacité perçue" (confusion sur comment rejoindre le live) — principal frein à la présence. En répondant aux questions pratiques avant qu\'elles soient posées, on supprime la friction d\'entrée.',
        message: [
          '{{1}}, dans 2 jours ça commence ! 📅',
          '',
          'Quelques infos pratiques avant le début du Challenge :',
          '',
          '✅ Les sessions ont lieu en direct sur StreamYard',
          '✅ Tu recevras le lien 2h avant chaque session par ici (WhatsApp)',
          '✅ Durée prévue : environ [DURÉE] par session',
          '✅ Pas besoin de créer de compte — le lien suffit',
          '✅ Si tu rates une session, tu peux rejoindre la suivante',
          '',
          'Des questions avant le début ? Je suis là 👇',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          '[À PERSONNALISER] : remplacer [DURÉE] par la durée réelle de tes sessions',
          'Ce message réduit le taux d\'absence dû à la confusion logistique — ne pas le sous-estimer',
        ],
        placeholder: true,
      },
      {
        num: 7,
        key: 'countdown_j1',
        name: 'J-1 — La veille du premier live',
        timing: 'J-1 avant le challenge',
        audience: 'Tous les inscrits',
        vars: [
          { v: '{{1}}', d: 'Prénom du contact' },
          { v: '{{2}}', d: 'Heure de la 1ère session (ex : "21h00" pour EU, "19h00" pour US-CA)' },
        ],
        trigger: 'Broadcast automatique J-1 — {{2}} injecté depuis la config cohort',
        lever: 'Biais du Présent + Rareté (Present Bias + Scarcity)',
        psychDesc: 'Le Present Bias pousse à valoriser l\'immédiat sur le futur. "Demain" est maintenant concret — l\'heure est connue, le rendez-vous est posé. La mention que la session n\'est pas rediffusée active la rareté : c\'est unique et limité dans le temps. Ce message doit créer une légère urgence sans manipulation.',
        message: [
          '{{1}} — demain, ça commence ! 🚀',
          '',
          'La première session du Challenge Amazon FBA a lieu demain à {{2}}.',
          '',
          'Tu recevras ton lien d\'accès directement ici, 2h avant.',
          '',
          'Ce live n\'est pas rediffusé — assure-toi d\'être disponible.',
          '',
          'À demain ! 💪',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variables : {{1}} prénom, {{2}} heure',
          '{{2}} est injecté automatiquement depuis la config cohort (EU : "21h00", US-CA : "19h00")',
          'Volontairement court — c\'est l\'effet recherché : un rendez-vous clair, pas un long message',
        ],
        placeholder: false,
      },
    ],
  },

  // ═══════════════════════════════ JOUR 1 ══════════════════════════════════════
  {
    phaseTitle: 'PHASE 2 — Jour 1 (Premier live)',
    phaseColor: C.green,
    phaseBg: C.greenBg,
    phaseDesc: 'Un seul message pour tout le monde — c\'est le premier live, il n\'y a pas encore d\'historique de présence. Envoyé 2h avant le début.',
    templates: [
      {
        num: 8,
        key: 'live_day1',
        name: 'Live Jour 1 — Rappel universel (2h avant)',
        timing: 'Jour 1, 2h avant le live',
        audience: 'Tous les inscrits actifs',
        vars: [
          { v: '{{1}}', d: 'Prénom du contact' },
          { v: '{{2}}', d: 'URL StreamYard de la Session 1' },
          { v: '{{3}}', d: 'Heure de la session (ex : "21h00")' },
        ],
        trigger: 'Webhook StreamYard session { day_number: 1 } → broadcast automatique 2h avant',
        lever: 'Rareté + Biais du Présent (Scarcity + Present Bias)',
        psychDesc: 'La rareté ("ce live n\'est pas rediffusé") augmente la valeur perçue et crée l\'urgence d\'agir maintenant. Le lien direct réduit l\'énergie d\'activation (BJ Fogg) : un clic suffit. La mention du programme crée une dernière vague d\'anticipation.',
        message: [
          '🚨 {{1}}, c\'est dans 2h !',
          '',
          'Le Challenge Amazon FBA — Session 1 commence à {{3}}.',
          '',
          '📹 Ton lien d\'accès :',
          '{{2}}',
          '',
          'Au programme ce soir :',
          '→ [POINT CLÉ SESSION 1]',
          '→ [POINT CLÉ SESSION 1]',
          '→ [POINT CLÉ SESSION 1]',
          '',
          'Ce live n\'est pas rediffusé — sois là ! 🎯',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variables : {{1}} prénom, {{2}} URL, {{3}} heure',
          '[À PERSONNALISER] : remplacer les 3 points clés par le vrai programme de ta Session 1',
          'Le lien {{2}} doit être sur sa propre ligne — plus visible sur mobile',
        ],
        placeholder: true,
      },
    ],
  },

  // ═══════════════════════════════ JOUR 2 ══════════════════════════════════════
  {
    phaseTitle: 'PHASE 3 — Jour 2 (3 messages selon la présence à J1)',
    phaseColor: C.amber,
    phaseBg: C.amberBg,
    phaseDesc: 'StreamYard fournit 3 catégories de contacts après chaque live : (A) présents au live, (B) inscrits sur StreamYard mais absents, (C) pas inscrits du tout sur StreamYard. Chaque catégorie reçoit un message différent.',
    templates: [
      {
        num: 9,
        key: 'live_day2_attended',
        name: 'Jour 2 — Pour ceux qui ont assisté à J1',
        timing: 'Jour 2, 2h avant le live',
        audience: 'Contacts avec événement day1_live_joined (présents Session 1)',
        vars: [
          { v: '{{1}}', d: 'Prénom du contact' },
          { v: '{{2}}', d: 'URL StreamYard Session 2' },
          { v: '{{3}}', d: 'Heure de la session' },
        ],
        trigger: 'Broadcast J2 × filtre : ScoreEvent day1_live_joined existe',
        lever: 'Effet Goal-Gradient (progrès vers l\'objectif)',
        psychDesc: 'Hull (1932) : l\'effort et la motivation augmentent à mesure qu\'on se rapproche d\'un objectif. "2 sur 3" crée le sentiment concret d\'être presque arrivé. Féliciter la présence à J1 active aussi la réciprocité et renforce l\'identité positive ("je suis quelqu\'un qui passe à l\'action").',
        message: [
          '{{1}}, tu étais là hier soir — bravo ! 👏',
          '',
          'Tu fais partie des personnes qui passent à l\'action. Ce soir, on va plus loin.',
          '',
          'Session 2 à {{3}} — le sujet : [RÉSUMÉ SESSION 2]',
          '',
          '📹 {{2}}',
          '',
          '2 sessions sur 3 — tu es à mi-chemin de ta transformation. 💪',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variables : {{1}}, {{2}}, {{3}}',
          '[À PERSONNALISER] : remplacer [RÉSUMÉ SESSION 2] par le vrai sujet de ta Session 2',
          'Ton volontairement positif et valorisant — ce contact est ton public le plus engagé',
        ],
        placeholder: true,
      },
      {
        num: 10,
        key: 'live_day2_registered_absent',
        name: 'Jour 2 — Pour ceux inscrits StreamYard J1 mais absents',
        timing: 'Jour 2, 2h avant le live',
        audience: 'Contacts avec day1_streamyard_registered mais pas day1_live_joined',
        vars: [
          { v: '{{1}}', d: 'Prénom du contact' },
          { v: '{{2}}', d: 'URL StreamYard Session 2' },
          { v: '{{3}}', d: 'Heure de la session' },
        ],
        trigger: 'Broadcast J2 × filtre : inscrit StreamYard J1 mais pas de day1_live_joined',
        lever: 'Aversion à la Perte douce (Loss Aversion)',
        psychDesc: 'Kahneman : les pertes pèsent 2× plus que les gains. "Tu avais réservé ta place" rappelle un engagement pris — ne pas venir ce soir serait perdre une deuxième fois. La formulation est empathique (pas de culpabilisation) mais active subtilement le FOMO. La "deuxième chance" est explicitement offerte.',
        message: [
          'Bonjour {{1}} 👋',
          '',
          'Tu avais réservé ta place pour la Session 1 hier soir — mais tu n\'as pas pu être là.',
          '',
          'Pas de souci. Ce soir à {{3}}, la Session 2 est encore accessible :',
          '',
          '→ [RÉSUMÉ SESSION 2 en 1 ligne]',
          '',
          '📹 {{2}}',
          '',
          'C\'est ta deuxième chance — saisis-la. 🙌',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variables : {{1}}, {{2}}, {{3}}',
          '[À PERSONNALISER] : résumé Session 2 en une ligne accrocheuse',
          'Ce filtre nécessite de soumettre les inscrits StreamYard J1 via POST /webhooks/streamyard/attendance avec statut "registered" (voir doc technique)',
        ],
        placeholder: true,
      },
      {
        num: 11,
        key: 'live_day2_not_registered',
        name: 'Jour 2 — Pour ceux n\'ayant pas du tout interagi avec J1',
        timing: 'Jour 2, 2h avant le live',
        audience: 'Contacts sans aucune interaction StreamYard J1',
        vars: [
          { v: '{{1}}', d: 'Prénom du contact' },
          { v: '{{2}}', d: 'URL StreamYard Session 2' },
          { v: '{{3}}', d: 'Heure de la session' },
        ],
        trigger: 'Broadcast J2 × filtre : pas de ScoreEvent day1_* pour ce contact',
        lever: 'Fresh Start Effect + Réciprocité',
        psychDesc: 'Le Fresh Start Effect (Milkman) : un nouveau départ efface la "ardoise" et relance la motivation. Ce message n\'évoque pas l\'absence à J1 — il présente J2 comme un point de départ frais. La question "qu\'est-ce qui t\'en a empêché" ouvre aussi une conversation utile pour l\'agent IA.',
        message: [
          'Bonjour {{1}} ! 😊',
          '',
          'Tu t\'es inscrit(e) au Challenge Amazon FBA — ce soir à {{3}}, la Session 2 est ouverte :',
          '',
          '→ [RÉSUMÉ SESSION 2 — la promesse principale]',
          '',
          '📹 {{2}}',
          '',
          'Ce soir, c\'est un bon moment pour commencer. Rejoins-nous ! 🎯',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variables : {{1}}, {{2}}, {{3}}',
          'Ne pas mentionner l\'absence à J1 — ne pas culpabiliser, juste re-engager',
          'Ton positif et sans reproche — l\'objectif est de les faire venir à J2, peu importe le passé',
        ],
        placeholder: true,
      },
    ],
  },

  // ═══════════════════════════════ JOUR 3 ══════════════════════════════════════
  {
    phaseTitle: 'PHASE 4 — Jour 3 (3 messages selon la présence à J2)',
    phaseColor: C.purple,
    phaseBg: C.purpleBg,
    phaseDesc: 'Même logique que Jour 2 mais appliquée à la présence à la Session 2. La Session 3 est la plus importante — c\'est là que l\'offre est présentée.',
    templates: [
      {
        num: 12,
        key: 'live_day3_attended',
        name: 'Jour 3 — Pour ceux présents à J2',
        timing: 'Jour 3, 2h avant le live',
        audience: 'Contacts avec événement day2_live_joined',
        vars: [
          { v: '{{1}}', d: 'Prénom du contact' },
          { v: '{{2}}', d: 'URL StreamYard Session 3' },
          { v: '{{3}}', d: 'Heure de la session' },
        ],
        trigger: 'Broadcast J3 × filtre : ScoreEvent day2_live_joined existe',
        lever: 'Règle du Pic et de la Fin (Peak-End Rule)',
        psychDesc: 'Kahneman : on juge une expérience par son moment le plus intense (pic) et sa conclusion (fin). Positionner la Session 3 comme "la plus importante" et "le moment où tout se joue" crée l\'anticipation d\'un pic mémorable. La "surprise" (l\'offre) ancre positivement la fin du parcours.',
        message: [
          '{{1}} — ce soir, c\'est LA session ! 🏆',
          '',
          'Tu as tout suivi depuis le début. Ce soir à {{3}}, on ferme la boucle :',
          '',
          '→ [RÉSUMÉ SESSION 3 — les étapes concrètes]',
          '→ Et une surprise pour ceux qui veulent aller plus loin 🎁',
          '',
          '📹 {{2}}',
          '',
          'C\'est ce soir que tout se joue. Sois là ! 🔥',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variables : {{1}}, {{2}}, {{3}}',
          '[À PERSONNALISER] : résumé Session 3 en points clés depuis StreamYard',
          'La "surprise" = l\'offre de formation — adapter le mot si tu préfères "une annonce" ou "une proposition"',
        ],
        placeholder: true,
      },
      {
        num: 13,
        key: 'live_day3_registered_absent',
        name: 'Jour 3 — Pour ceux inscrits J2 mais absents',
        timing: 'Jour 3, 2h avant le live',
        audience: 'Contacts avec day2_streamyard_registered mais pas day2_live_joined',
        vars: [
          { v: '{{1}}', d: 'Prénom du contact' },
          { v: '{{2}}', d: 'URL StreamYard Session 3' },
          { v: '{{3}}', d: 'Heure de la session' },
        ],
        trigger: 'Broadcast J3 × filtre : inscrit J2 mais pas de day2_live_joined',
        lever: 'Aversion à la Perte + Urgence Authentique',
        psychDesc: 'Cette session finale ne peut pas être manquée sans conséquence : c\'est là que l\'offre est présentée. L\'urgence ici est authentique et éthique. La formulation "dernière chance" est factuelle, pas manipulatrice. Le ton reste bienveillant pour ne pas fermer la porte.',
        message: [
          '{{1}}, la dernière session du Challenge — c\'est ce soir ! ⏰',
          '',
          'Ce soir à {{3}} : [RÉSUMÉ SESSION 3]',
          '',
          '📹 {{2}}',
          '',
          'Tu n\'as pas pu être là à toutes les sessions — mais celle-ci est la plus importante.',
          '',
          'C\'est ta dernière chance dans cette édition. Ne la laisse pas passer. 💙',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variables : {{1}}, {{2}}, {{3}}',
          'Ton de légère urgence — éthique car la Session 3 est réellement la plus importante (offre)',
          'Ne pas mentionner explicitement l\'offre dans le template (règle Meta)',
        ],
        placeholder: true,
      },
      {
        num: 14,
        key: 'live_day3_not_registered',
        name: 'Jour 3 — Pour ceux n\'ayant jamais interagi avec un live',
        timing: 'Jour 3, 2h avant le live',
        audience: 'Contacts sans aucune interaction StreamYard sur J1 ou J2',
        vars: [
          { v: '{{1}}', d: 'Prénom du contact' },
          { v: '{{2}}', d: 'URL StreamYard Session 3' },
          { v: '{{3}}', d: 'Heure de la session' },
        ],
        trigger: 'Broadcast J3 × filtre : aucun ScoreEvent day1_* ou day2_*',
        lever: 'Comptabilité Mentale + Appel à l\'engagement initial',
        psychDesc: 'Thaler (Mental Accounting) : ils ont déjà "investi" en s\'inscrivant. Ne pas venir, c\'est perdre cet investissement. La question directe "qu\'est-ce qui t\'en a empêché" ouvre un dialogue qui alimente l\'agent IA. Ce message ne vend pas — il cherche à comprendre pour mieux accompagner.',
        message: [
          'Bonjour {{1}} 👋',
          '',
          'Tu t\'es inscrit(e) au Challenge Amazon FBA, mais on ne s\'est pas encore croisé(e)s en live.',
          '',
          'Ce soir à {{3}}, c\'est la dernière session de cette édition :',
          '',
          '📹 {{2}}',
          '',
          '❓ Qu\'est-ce qui t\'a empêché(e) jusqu\'ici ?',
          '',
          'Réponds-moi — et viens ce soir si tu peux. 🙏',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variables : {{1}}, {{2}}, {{3}}',
          'Objectif principal : comprendre le frein (alimenter l\'agent IA) + présenter la dernière chance',
          'Les réponses à ce message sont précieuses pour améliorer la prochaine édition',
        ],
        placeholder: false,
      },
    ],
  },

  // ═══════════════════════════════ POST-CHALLENGE ═══════════════════════════════
  {
    phaseTitle: 'PHASE 5 — Post-challenge (J+1 et J+2)',
    phaseColor: C.red,
    phaseBg: C.redBg,
    phaseDesc: 'Après la dernière session : 3 messages distincts selon le niveau de participation, puis un message final universel à J+2.',
    templates: [
      {
        num: 15,
        key: 'post_recap_attended',
        name: 'J+1 — Pour ceux qui ont suivi la Session 3',
        timing: 'J+1, 24h après la fin de la Session 3',
        audience: 'Contacts avec événement day3_live_joined (ont assisté au live final)',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: '24h après la Session 3 × filtre : day3_live_joined existe',
        lever: 'Réciprocité + Pied-dans-la-porte (Foot-in-the-Door)',
        psychDesc: 'Cialdini : donner de la valeur (félicitations sincères + question) crée une dette de réciprocité. Le Foot-in-the-Door : chaque petit engagement (répondre ici) prépare à un plus grand (l\'offre). Ce message ne vend pas — il construit le pont. La vente arrive dans post_followup (J+2).',
        message: [
          '🎉 {{1}}, bravo — tu as fait les 3 sessions !',
          '',
          'Tu fais partie d\'un petit groupe qui a tout suivi depuis le début. Ça dit quelque chose sur toi.',
          '',
          'Une question : qu\'est-ce qui t\'a le plus marqué(e) dans ce challenge ?',
          '',
          'Réponds-moi ici — je reviens vers toi dans les prochaines heures avec la suite. 👇',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          'Pas de CTA vers l\'offre dans ce message — la vente arrive dans post_followup',
          'Les réponses reçues ici sont des témoignages potentiels — les noter dans le dashboard',
        ],
        placeholder: false,
      },
      {
        num: 16,
        key: 'post_recap_registered_absent',
        name: 'J+1 — Pour ceux peu présents (inscrits mais peu de lives)',
        timing: 'J+1, 24h après la fin de la Session 3',
        audience: 'Contacts avec 1 ou 2 lives suivis (ont participé partiellement)',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: '24h après J3 × filtre : 1-2 ScoreEvents day{N}_live_joined',
        lever: 'FOMO + Porte entrouverte',
        psychDesc: 'Fear Of Missing Out activé par le récap de ce qui a été manqué. Plutôt que de "fermer la porte", on maintient une porte entrouverte — technique de maintien de relation qui préserve l\'option pour la prochaine cohorte ou l\'offre actuelle. Le ton empathique préserve la relation à long terme.',
        message: [
          'Bonjour {{1}} 👋',
          '',
          'Le Challenge Amazon FBA vient de se terminer.',
          '',
          'La Session 3 d\'hier soir a été intense — on a couvert [POINT CLÉ J3] et annoncé quelque chose d\'important pour ceux qui veulent aller plus loin.',
          '',
          'Si tu veux savoir ce qui a été partagé, réponds-moi "INFO" ici.',
          '',
          'Je reste disponible pour toi. 🙌',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          '[À PERSONNALISER] : remplacer [POINT CLÉ J3] par le vrai highlight de la Session 3',
          'Le "réponds INFO" est un signal d\'intérêt que l\'agent IA capte et escalade à l\'équipe',
        ],
        placeholder: true,
      },
      {
        num: 17,
        key: 'post_recap_not_registered',
        name: 'J+1 — Pour ceux qui n\'ont jamais participé à un live',
        timing: 'J+1, 24h après la fin de la Session 3',
        audience: 'Contacts sans aucune interaction StreamYard sur les 3 jours',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: '24h après J3 × filtre : aucun ScoreEvent day{N}_live_joined',
        lever: 'Regret Aversion + Prochaine cohorte',
        psychDesc: 'Plutôt que de rappeler ce qui a été manqué (aversion au regret déjà activée), on tourne la page positivement. Proposer d\'être "notifié en priorité" pour la prochaine édition maintient le contact dans le pipeline sans friction. C\'est la stratégie long terme : ne pas brûler la relation.',
        message: [
          'Bonjour {{1}},',
          '',
          'Le Challenge Amazon FBA vient de se terminer — les 3 sessions live ont eu lieu.',
          '',
          'Tu t\'étais inscrit(e), mais quelque chose t\'a empêché(e) de participer.',
          '',
          '❓ Si tu veux me dire ce qui t\'a bloqué(e), je t\'écoute.',
          '',
          'Et si tu veux être notifié(e) en priorité pour la prochaine édition, dis-le-moi ici. 👇',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          'Objectif : comprendre le frein + maintenir le contact pour la prochaine cohorte',
          'Ne pas parler de l\'offre ici — ces contacts ne sont pas encore qualifiés',
        ],
        placeholder: false,
      },
      {
        num: 18,
        key: 'post_followup',
        name: 'J+2 — Dernier message universel (offre finale)',
        timing: 'J+2, 48h après la fin de la Session 3',
        audience: 'Tous les contacts encore actifs dans la séquence',
        vars: [{ v: '{{1}}', d: 'Prénom du contact' }],
        trigger: '48h après J3 — tous contacts (sauf désinscriptions)',
        lever: 'Ancrage de Valeur + Dernière Chance douce',
        psychDesc: 'L\'ancrage (Anchoring) rappelle ce qui a été reçu gratuitement avant de parler de l\'offre payante. Le "OUI" comme CTA réduit la friction au maximum (1 mot = action). La formulation "dernier message" est honnête et crée une urgence authentique. Elle préserve la relation à long terme même si le contact ne convertit pas.',
        message: [
          '{{1}}, c\'est mon dernier message pour ce challenge. 😊',
          '',
          'En 3 sessions gratuites, tu as eu accès à [CE QUE TU AS DONNÉ — méthode, stratégie, outils].',
          '',
          'Si tu veux être accompagné(e) pour mettre tout ça en pratique et éviter les erreurs de départ :',
          '',
          'Réponds simplement "OUI" ici et je t\'envoie tous les détails. 👇',
          '',
          'Quoi qu\'il arrive, merci d\'avoir été là. 🙏',
        ],
        notes: [
          'Catégorie : MARKETING | Langue : fr | Variable : {{1}} = prénom uniquement',
          '[À PERSONNALISER] : remplacer [CE QUE TU AS DONNÉ] par les 3 choses les plus précieuses partagées',
          'Le "OUI" déclenche l\'agent IA qui escalade le contact à l\'équipe commerciale',
          'C\'est le seul message avec un CTA de vente explicite (mais très doux)',
        ],
        placeholder: true,
      },
    ],
  },
];

// ─── DOCUMENT BUILD ───────────────────────────────────────────────────────────
function buildDoc() {
  const children = [];

  // ── PAGE DE COUVERTURE ────────────────────────────────────────────────────────
  children.push(
    ...sp(5),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 },
      children: [br('CHALLENGE AMAZON FBA', { size: 52, color: C.primaryDk })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
      children: [r('Séquence de messages WhatsApp — Version 2.0', { size: 32, color: C.primary })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
      children: [r('18 templates • Logique de personnalisation • EU & USA', { size: 22, color: C.gray400, italics: true })] }),
    ...sp(2),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
      children: [r('Réponse au retour client du [DATE] — Document de validation v2', { size: 20, color: C.amber, bold: true })] }),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── RÉPONSES AUX RETOURS CLIENT ───────────────────────────────────────────────
  children.push(
    h1('1. Réponses à vos retours'),
    body('Chaque point soulevé a été pris en compte dans cette version 2.0. Voici ce qui change et pourquoi.'),
    ...sp(1),

    h2('✅ Retour 1 — "Je ne vois que J-7 et J-6"'),
    body('Résolu. La séquence passe de 2 messages de préparation à 7 (un par jour de J-7 à J-1). Chaque message a un objectif distinct : bienvenue, question conversationnelle, curiosité, social proof, teaser du programme, logistique, et compte à rebours final.'),
    ...sp(1),

    h2('✅ Retour 2 — "Ceux qui s\'inscrivent à J-3 ne reçoivent pas le message de bienvenue"'),
    body('Résolu. Le message de bienvenue (welcome) est maintenant envoyé immédiatement à l\'inscription, sans référence temporelle ("7 jours avant" a été supprimé). Le système calcule ensuite le nombre de jours restants et démarre la séquence countdown au bon endroit. Un inscrit à J-3 reçoit : welcome (immédiat) → countdown_j3 → countdown_j2 → countdown_j1 → live_day1.'),
    ...sp(1),

    h2('✅ Retour 3 — "Europe et USA ne reçoivent pas les mêmes liens ni les mêmes horaires"'),
    body('C\'était déjà géré côté technique. Pour clarifier : la plateforme gère deux "cohortes" — EU (21h00, heure de Paris) et US-CA (19h00, heure de Montréal). Chaque contact est assigné à une cohorte à l\'inscription. Les variables {{2}} (lien StreamYard) et {{3}} (heure) sont injectées différemment selon la cohorte. Côté Systeme.io, il faudra deux funnels séparés (un par région) ou un champ de segmentation dans le formulaire d\'inscription.'),
    ...sp(1),

    h2('✅ Retour 4 — "Comment savoir si quelqu\'un a participé au live ?"'),
    body('StreamYard vous donne après chaque session la liste des participants. Cette liste est soumise à notre système via un simple envoi (ou automatisé via Zapier). Le système gère 3 états distincts — voir le retour suivant.'),
    ...sp(1),

    h2('✅ Retour 5 — "3 situations sur StreamYard : présent / inscrit absent / pas inscrit"'),
    body('Résolu. La version 2.0 intègre exactement ces 3 états pour les Jours 2, 3 et J+1 :'),
    ...sp(1),
    new Table({
      width: { size: 9360, type: WidthType.DXA }, columnWidths: [3000, 2200, 4160],
      rows: [
        new TableRow({ tableHeader: true, children: [
          ['État StreamYard', 3000], ['Événement système', 2200], ['Template envoyé', 4160],
        ].map(([t, w]) => new TableCell({
          width: { size: w, type: WidthType.DXA }, borders: cb(C.primary),
          shading: { type: ShadingType.CLEAR, fill: C.primaryDk },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [br(t, { size: 18, color: C.white })] })],
        })) }),
        ...([
          ['A assisté au live', 'day{N}_live_joined', 'Template "attended" — continuité'],
          ['Inscrit StreamYard, absent', 'day{N}_streamyard_registered', 'Template "registered_absent" — FOMO doux'],
          ['Pas inscrit du tout', '(aucun événement)', 'Template "not_registered" — re-engagement'],
        ].map(([a, b, c], i) => new TableRow({ children: [
          new TableCell({ width: { size: 3000, type: WidthType.DXA }, borders: cb(C.gray200),
            shading: { type: ShadingType.CLEAR, fill: i % 2 === 0 ? C.white : C.gray50 },
            margins: { top: 60, bottom: 60, left: 120, right: 120 },
            children: [new Paragraph({ children: [r(a, { size: 18 })] })] }),
          new TableCell({ width: { size: 2200, type: WidthType.DXA }, borders: cb(C.gray200),
            shading: { type: ShadingType.CLEAR, fill: C.greenBg },
            margins: { top: 60, bottom: 60, left: 120, right: 120 },
            children: [new Paragraph({ children: [r(b, { size: 16, color: C.green, italics: true })] })] }),
          new TableCell({ width: { size: 4160, type: WidthType.DXA }, borders: cb(C.gray200),
            margins: { top: 60, bottom: 60, left: 120, right: 120 },
            children: [new Paragraph({ children: [r(c, { size: 18 })] })] }),
        ]})))
      ],
    }),
    ...sp(1),

    h2('✅ Retour 6 — "Pas de messages conversationnels"'),
    body('Résolu. Chaque message se termine maintenant par une question ouverte ou un CTA de réponse ("Réponds-moi ici 👇"). Les réponses sont captées par l\'agent IA qui les traite et les fait remonter aux opérateurs si nécessaire. Les messages broadcast deviennent des points de départ de conversation.'),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── VUE D'ENSEMBLE ────────────────────────────────────────────────────────────
  children.push(
    h1('2. Architecture de la séquence — Vue d\'ensemble'),
    ...sp(1),
  );

  const overviewRows = [
    ['#', 'Clé Wati', 'Phase', 'Timing', 'Audience', 'Levier principal'],
    ...PHASES.flatMap(phase =>
      phase.templates.map(t => [
        String(t.num), t.key, phase.phaseTitle.split('—')[0].trim(),
        t.timing.split(',')[0], t.audience.substring(0, 35) + (t.audience.length > 35 ? '…' : ''), t.lever.split('(')[0].trim(),
      ])
    ),
  ];

  const colW = [400, 2300, 1200, 1500, 1900, 2060];
  children.push(
    new Table({
      width: { size: 9360, type: WidthType.DXA }, columnWidths: colW,
      rows: overviewRows.map((row, ri) => new TableRow({
        tableHeader: ri === 0,
        children: row.map((cell, ci) => new TableCell({
          width: { size: colW[ci], type: WidthType.DXA },
          borders: cb(ri === 0 ? C.primary : C.gray200),
          shading: { type: ShadingType.CLEAR, fill: ri === 0 ? C.primaryDk : ri % 2 === 0 ? C.white : C.gray50 },
          margins: { top: 60, bottom: 60, left: 80, right: 80 },
          children: [new Paragraph({ children: [r(cell, { size: 16, bold: ri === 0, color: ri === 0 ? C.white : C.gray700 })] })],
        })),
      })),
    }),
    ...sp(1),
    banner([
      'Note sur les placeholders',
      '12 des 18 messages contiennent des sections [À PERSONNALISER] signalées en orange dans les fiches détaillées. Ces sections doivent être remplies avec le vrai contenu de vos sessions StreamYard. Il serait utile de partager le lien StreamYard ou un résumé des 3 sessions pour finaliser ces messages.',
    ], C.amberBg, C.amber, '⚠️'),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── LOGIQUE D'ENRÔLEMENT INTELLIGENT ─────────────────────────────────────────
  children.push(
    h1('3. Logique d\'enrôlement intelligent (inscriptions tardives)'),
    body('Un contact qui s\'inscrit à J-3 doit recevoir le welcome immédiatement, puis démarrer la séquence à countdown_j3 (pas à countdown_j6). Voici la règle :'),
    ...sp(1),
    twoColTable([
      ['Inscription à J-7', 'welcome → countdown_j6 → j5 → j4 → j3 → j2 → j1 → live_day1'],
      ['Inscription à J-5', 'welcome → countdown_j5 → j4 → j3 → j2 → j1 → live_day1'],
      ['Inscription à J-3', 'welcome → countdown_j3 → j2 → j1 → live_day1'],
      ['Inscription à J-1', 'welcome → countdown_j1 → live_day1'],
      ['Inscription le Jour 1', 'welcome → live_day1 (directement)'],
      ['Inscription après J1', 'welcome → live_day2 ou live_day3 selon le jour'],
    ], 2000, 7360),
    ...sp(1),
    infoBox([
      'Comment ça fonctionne techniquement',
      'À l\'inscription (webhook Systeme.io), le système calcule le nombre de jours restants avant le début du challenge (date stockée dans ChallengeEdition). Il démarre l\'enrollment au step correspondant. Le welcome est toujours envoyé en premier, quelle que soit la date.',
    ]),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── EU vs USA ─────────────────────────────────────────────────────────────────
  children.push(
    h1('4. Gestion des cohortes EU et USA'),
    body('Chaque inscrit est assigné à une cohorte. Les variables {{2}} (lien live) et {{3}} (heure) sont injectées différemment selon la cohorte.'),
    ...sp(1),
    twoColTable([
      ['Cohorte EU', 'Heure live : 21h00 | Fuseau : Europe/Paris'],
      ['Cohorte US-CA', 'Heure live : 19h00 | Fuseau : America/Montreal'],
      ['Variable {{3}} EU', '"21h00"'],
      ['Variable {{3}} US-CA', '"19h00"'],
      ['Variable {{2}}', 'URL StreamYard — peut être différente par cohorte ou identique'],
      ['Assigner la cohorte', 'Via 2 funnels Systeme.io séparés (EU / US-CA) ou un champ "pays" à l\'inscription'],
    ], 2200, 7160),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── TEMPLATES DÉTAILLÉS ───────────────────────────────────────────────────────
  children.push(h1('5. Détail des 18 messages'));

  PHASES.forEach((phase, pi) => {
    children.push(
      new Paragraph({
        children: [br(phase.phaseTitle, { size: 26, color: phase.phaseColor })],
        spacing: { before: 320, after: 100 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 3, color: phase.phaseColor, space: 4 } },
      }),
      new Paragraph({
        children: [r(phase.phaseDesc, { size: 20, color: C.gray700, italics: true })],
        spacing: { before: 80, after: 80 },
        indent: { left: 240 },
      }),
    );

    phase.templates.forEach((t, ti) => {
      children.push(
        new Paragraph({
          children: [
            r(`Message ${t.num}/18  —  `, { size: 22, color: C.gray400 }),
            br(t.name, { size: 24, color: C.primaryDk }),
            ...(t.placeholder ? [r('  ⚠️ À personnaliser', { size: 18, color: C.amber, bold: true })] : []),
          ],
          spacing: { before: 280, after: 80 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: phase.phaseColor, space: 4 } },
        }),

        // Info table
        twoColTable([
          ['🏷️ Clé Wati', t.key],
          ['📅 Timing', t.timing],
          ['👥 Audience', t.audience],
          ['⚡ Déclencheur', t.trigger],
        ], 2000, 7360),
        ...sp(1),

        // Variables
        ...(t.vars.length > 0 ? [
          new Paragraph({ children: [br('Variables du message', { size: 20, color: C.gray700 })], spacing: { before: 80, after: 80 } }),
          new Table({
            width: { size: 9360, type: WidthType.DXA }, columnWidths: [1200, 8160],
            rows: [
              new TableRow({ tableHeader: true, children: [
                new TableCell({ width: { size: 1200, type: WidthType.DXA }, borders: cb(C.green),
                  shading: { type: ShadingType.CLEAR, fill: C.greenDk },
                  margins: { top: 60, bottom: 60, left: 120, right: 120 },
                  children: [new Paragraph({ children: [br('Variable', { size: 18, color: C.white })] })] }),
                new TableCell({ width: { size: 8160, type: WidthType.DXA }, borders: cb(C.green),
                  shading: { type: ShadingType.CLEAR, fill: C.greenDk },
                  margins: { top: 60, bottom: 60, left: 120, right: 120 },
                  children: [new Paragraph({ children: [br('Valeur injectée', { size: 18, color: C.white })] })] }),
              ]}),
              ...t.vars.map(({ v, d }) => new TableRow({ children: [
                new TableCell({ width: { size: 1200, type: WidthType.DXA }, borders: cb(C.gray200),
                  shading: { type: ShadingType.CLEAR, fill: C.greenBg },
                  margins: { top: 60, bottom: 60, left: 120, right: 120 },
                  children: [new Paragraph({ children: [br(v, { size: 18, color: C.green })] })] }),
                new TableCell({ width: { size: 8160, type: WidthType.DXA }, borders: cb(C.gray200),
                  margins: { top: 60, bottom: 60, left: 120, right: 120 },
                  children: [new Paragraph({ children: [r(d, { size: 18 })] })] }),
              ]})),
            ],
          }),
          ...sp(1),
        ] : []),

        psychBox(t.lever, t.psychDesc),
        ...sp(1),

        new Paragraph({ children: [br('💬 Texte du message WhatsApp', { size: 20, color: C.gray700 })], spacing: { before: 80, after: 80 } }),
        msgBox(t.message),
        ...sp(1),

        noteBox(['Configuration Wati', ...t.notes]),
        ...(ti < phase.templates.length - 1 ? [...sp(2)] : []),
      );

      if (pi < PHASES.length - 1 || ti < phase.templates.length - 1) {
        if ((t.num % 3 === 0)) children.push(new Paragraph({ children: [new PageBreak()] }));
      }
    });
  });

  // ── ÉTAPES SUIVANTES ─────────────────────────────────────────────────────────
  children.push(
    new Paragraph({ children: [new PageBreak()] }),
    h1('6. Étapes pour valider et mettre en ligne'),
    ...sp(1),
    h2('Étape 1 — Personnalisation du contenu (votre action)'),
    body('Remplir les 12 sections [À PERSONNALISER] avec le vrai contenu de vos sessions. En particulier : les 3 résumés de sessions dans countdown_j3 et live_day1/2/3, la durée des sessions dans countdown_j2, la valeur partagée dans post_followup.'),
    ...sp(1),
    h2('Étape 2 — Validation et retour'),
    body('Annoter ce document avec vos corrections et le retourner. Une fois validé, les 18 templates sont soumis à Wati puis à Meta pour approbation (délai habituel : 24-72h).'),
    ...sp(1),
    h2('Étape 3 — Mise en production'),
    body('Configuration des webhooks Systeme.io et StreamYard, tests sur numéros de test, puis lancement pour la prochaine édition du challenge.'),
    ...sp(2),
    new Table({
      width: { size: 9360, type: WidthType.DXA }, columnWidths: [9360],
      rows: [new TableRow({ children: [new TableCell({
        width: { size: 9360, type: WidthType.DXA }, borders: cb(C.gray200),
        shading: { type: ShadingType.CLEAR, fill: C.gray50 },
        margins: { top: 120, bottom: 120, left: 240, right: 240 },
        children: [
          new Paragraph({ alignment: AlignmentType.CENTER,
            children: [br('Document confidentiel — Version 2.0 — Pour validation client', { size: 18, color: C.gray700 })],
            spacing: { after: 60 } }),
          new Paragraph({ alignment: AlignmentType.CENTER,
            children: [r('18 templates | Architecture EU + USA | Personnalisation 3 états StreamYard | Enrôlement intelligent', { size: 16, color: C.gray400, italics: true })] }),
        ],
      })] })],
    }),
  );

  // ── ASSEMBLAGE ────────────────────────────────────────────────────────────────
  return new Document({
    numbering: { config: [] },
    styles: {
      default: { document: { run: { font: 'Arial', size: 20, color: C.black } } },
      paragraphStyles: [
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 30, bold: true, font: 'Arial', color: C.primaryDk },
          paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 24, bold: true, font: 'Arial', color: C.primary },
          paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
        { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 20, bold: true, font: 'Arial', color: C.gray700 },
          paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
      ],
    },
    sections: [{
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
      },
      headers: { default: new Header({ children: [
        new Paragraph({ children: [
          r('Challenge Amazon FBA — Messages WhatsApp v2.0', { size: 16, color: C.gray400 }),
          r('\t', {}), br('CONFIDENTIEL', { size: 16, color: C.amber }),
        ], tabStops: [{ type: 'right', position: 9360 }] }),
        new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: C.gray200, space: 1 } }, children: [] }),
      ]}) },
      footers: { default: new Footer({ children: [
        new Paragraph({ border: { top: { style: BorderStyle.SINGLE, size: 1, color: C.gray200, space: 1 } },
          children: [
            r('Version 2.0 — 18 templates — Mai 2026', { size: 16, color: C.gray400 }),
            r('\t', {}), r('Page ', { size: 16, color: C.gray400 }),
            new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 16, color: C.gray400 }),
          ], tabStops: [{ type: 'right', position: 9360 }] }),
      ]}) },
      children,
    }],
  });
}

const out = path.join(__dirname, 'messages-challenge-amazon-fba-v2.docx');
Packer.toBuffer(buildDoc()).then(buf => {
  fs.writeFileSync(out, buf);
  console.log(`✅  ${out}`);
  console.log(`📄  ${(buf.length/1024).toFixed(1)} KB`);
});
