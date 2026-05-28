const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, ExternalHyperlink,
  LevelFormat, UnderlineType
} = require('docx');
const fs = require('fs');
const path = require('path');

// ─── COLOR PALETTE ───────────────────────────────────────────────────────────
const C = {
  primary:     '1D4ED8', // blue-700
  primaryDark: '1E3A8A', // blue-900
  accent:      '10B981', // emerald-500
  accentDark:  '065F46', // emerald-800
  warning:     'D97706', // amber-600
  warningBg:   'FEF3C7', // amber-50
  purple:      '7C3AED', // violet-600
  purpleBg:    'EDE9FE', // violet-50
  infoBg:      'EFF6FF', // blue-50
  successBg:   'ECFDF5', // green-50
  lightGray:   'F8FAFC', // slate-50
  gray200:     'E2E8F0',
  gray400:     '94A3B8',
  gray700:     '334155',
  white:       'FFFFFF',
  black:       '0F172A',
};

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const cellBorder = (color = C.gray200) => ({
  top:    { style: BorderStyle.SINGLE, size: 1, color },
  bottom: { style: BorderStyle.SINGLE, size: 1, color },
  left:   { style: BorderStyle.SINGLE, size: 1, color },
  right:  { style: BorderStyle.SINGLE, size: 1, color },
});

const noBorder = () => ({
  top:    { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  left:   { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
  right:  { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
});

function p(children, opts = {}) {
  return new Paragraph({ children, ...opts });
}

function run(text, opts = {}) {
  return new TextRun({ text, font: 'Arial', ...opts });
}

function bold(text, opts = {}) {
  return run(text, { bold: true, ...opts });
}

function colored(text, color, opts = {}) {
  return run(text, { color, ...opts });
}

function spacer(lines = 1) {
  return Array.from({ length: lines }, () =>
    new Paragraph({ children: [new TextRun({ text: '', font: 'Arial' })] })
  );
}

function sectionHeading(title, level = 1) {
  if (level === 1) {
    return new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: title, font: 'Arial', bold: true, color: C.primaryDark, size: 32 })],
      spacing: { before: 400, after: 160 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.primary, space: 4 } },
    });
  }
  if (level === 2) {
    return new Paragraph({
      heading: HeadingLevel.HEADING_2,
      children: [new TextRun({ text: title, font: 'Arial', bold: true, color: C.primary, size: 26 })],
      spacing: { before: 280, after: 120 },
    });
  }
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text: title, font: 'Arial', bold: true, color: C.gray700, size: 22 })],
    spacing: { before: 200, after: 80 },
  });
}

function infoParagraph(text, bgColor = C.infoBg) {
  return new Paragraph({
    children: [new TextRun({ text, font: 'Arial', size: 20, color: C.gray700 })],
    shading: { type: ShadingType.CLEAR, fill: bgColor },
    spacing: { before: 60, after: 60 },
    indent: { left: 200, right: 200 },
  });
}

function labeledRow(label, value, labelColor = C.primaryDark) {
  return [
    new TableRow({
      children: [
        new TableCell({
          width: { size: 2200, type: WidthType.DXA },
          borders: cellBorder(C.gray200),
          shading: { type: ShadingType.CLEAR, fill: C.lightGray },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            children: [new TextRun({ text: label, font: 'Arial', bold: true, size: 18, color: labelColor })],
          })],
        }),
        new TableCell({
          width: { size: 7160, type: WidthType.DXA },
          borders: cellBorder(C.gray200),
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({
            children: [new TextRun({ text: value, font: 'Arial', size: 18, color: C.black })],
          })],
        }),
      ],
    }),
  ];
}

function messageBox(lines) {
  const children = [];
  lines.forEach((line, i) => {
    // Detect variable placeholders {{1}}, {{2}}, {{3}}
    const parts = line.split(/({{[^}]+}})/g);
    const runs = parts.map(part => {
      if (/^{{[^}]+}}$/.test(part)) {
        return new TextRun({ text: part, font: 'Arial', bold: true, color: C.accent, size: 20,
          shading: { type: ShadingType.CLEAR, fill: C.successBg } });
      }
      return new TextRun({ text: part, font: 'Arial', size: 20, color: C.black });
    });
    children.push(new Paragraph({
      children: runs,
      spacing: { before: i === 0 ? 0 : 60, after: 0 },
    }));
  });

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: 9360, type: WidthType.DXA },
            borders: {
              top:    { style: BorderStyle.SINGLE, size: 2, color: C.accent },
              bottom: { style: BorderStyle.SINGLE, size: 2, color: C.accent },
              left:   { style: BorderStyle.THICK,  size: 12, color: C.accent },
              right:  { style: BorderStyle.SINGLE, size: 2, color: C.accent },
            },
            shading: { type: ShadingType.CLEAR, fill: C.successBg },
            margins: { top: 120, bottom: 120, left: 200, right: 200 },
            children,
          }),
        ],
      }),
    ],
  });
}

function psychBox(lever, description) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: 9360, type: WidthType.DXA },
            borders: {
              top:    { style: BorderStyle.SINGLE, size: 2, color: C.purple },
              bottom: { style: BorderStyle.SINGLE, size: 2, color: C.purple },
              left:   { style: BorderStyle.THICK,  size: 12, color: C.purple },
              right:  { style: BorderStyle.SINGLE, size: 2, color: C.purple },
            },
            shading: { type: ShadingType.CLEAR, fill: C.purpleBg },
            margins: { top: 100, bottom: 100, left: 200, right: 200 },
            children: [
              new Paragraph({
                children: [
                  new TextRun({ text: '🧠  Levier psychologique : ', font: 'Arial', bold: true, size: 18, color: C.purple }),
                  new TextRun({ text: lever, font: 'Arial', bold: true, size: 18, color: C.purpleDark }),
                ],
                spacing: { after: 60 },
              }),
              new Paragraph({
                children: [new TextRun({ text: description, font: 'Arial', size: 18, color: C.gray700, italics: true })],
              }),
            ],
          }),
        ],
      }),
    ],
  });
}

function watiBox(notes) {
  const children = notes.map((note, i) => new Paragraph({
    children: [new TextRun({ text: `${i + 1}.  ${note}`, font: 'Arial', size: 18, color: C.gray700 })],
    spacing: { before: i === 0 ? 0 : 60, after: 0 },
  }));
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: 9360, type: WidthType.DXA },
            borders: {
              top:    { style: BorderStyle.SINGLE, size: 2, color: C.warning },
              bottom: { style: BorderStyle.SINGLE, size: 2, color: C.warning },
              left:   { style: BorderStyle.THICK,  size: 12, color: C.warning },
              right:  { style: BorderStyle.SINGLE, size: 2, color: C.warning },
            },
            shading: { type: ShadingType.CLEAR, fill: C.warningBg },
            margins: { top: 100, bottom: 100, left: 200, right: 200 },
            children: [
              new Paragraph({
                children: [new TextRun({ text: '⚙️  Configuration Wati', font: 'Arial', bold: true, size: 18, color: C.warning })],
                spacing: { after: 80 },
              }),
              ...children,
            ],
          }),
        ],
      }),
    ],
  });
}

// ─── TEMPLATE DATA ────────────────────────────────────────────────────────────
const templates = [
  {
    num: 1,
    key: 'welcome_j7',
    name: 'Bienvenue — 7 jours avant le challenge',
    step: 'J-7 (7 jours avant le début)',
    audience: 'Tous les inscrits au challenge',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact (ex : Sophie)' },
    ],
    trigger: 'Inscription confirmée dans Systeme.io → webhook → campagne démarrée à J-7',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Engagement & Cohérence (Commitment & Consistency)',
    psychDesc: 'Cialdini : une fois qu\'une personne a dit "oui" à une petite action (inscription), elle ressent une pression interne à rester cohérente. En l\'invitant à bloquer les dates dans son agenda, on solidifie l\'engagement comportemental dès le départ. Cette "micro-action" augmente significativement le taux de présence au challenge.',
    message: [
      '🌟 Bonjour {{1}} !',
      '',
      'Bienvenue dans l\'aventure Challenge Amazon FBA ! 🚀',
      '',
      'Tu t\'es inscrit(e) à 3 sessions live qui vont transformer ta façon de voir le business en ligne. Je suis enthousiaste à l\'idée de te guider dans cette aventure.',
      '',
      '📅 Bloque ces dates dans ton agenda maintenant :',
      '→ Jour 1 : La méthode FBA de A à Z',
      '→ Jour 2 : Trouver et sourcer ton produit gagnant',
      '→ Jour 3 : Lancer et scaler sur Amazon',
      '',
      'Ces 3 sessions = les fondations de ta liberté financière.',
      '',
      'À très vite ! 🙌',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Variable {{1}} = champ "First Name" du contact Wati',
      'Délai d\'envoi : 0 minute après le déclencheur d\'inscription',
      'Bouton optionnel : "Ajouter à mon agenda" (lien Google Calendar)',
    ],
  },
  {
    num: 2,
    key: 'content_j6',
    name: 'Contenu de préparation — 6 jours avant',
    step: 'J-6 (6 jours avant le début)',
    audience: 'Tous les inscrits (suite de la séquence bienvenue)',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
    ],
    trigger: '24h après l\'envoi du message welcome_j7',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Present Bias + Effet Zeigarnik',
    psychDesc: 'Le Present Bias pousse à préférer l\'action maintenant plutôt que plus tard. En posant une question ouverte (la principale difficulté), on ouvre une "boucle cognitive" (Zeigarnik) : le cerveau reste en suspension jusqu\'à ce qu\'il obtienne une réponse. Cette tension pousse le contact à s\'engager activement et à attendre le contenu des sessions.',
    message: [
      'Bonjour {{1}} 👋',
      '',
      'À J-6 du challenge, j\'ai une question pour toi :',
      '',
      '❓ Quelle est ta principale difficulté aujourd\'hui quand tu penses à lancer sur Amazon ?',
      '',
      'Réponds-moi ici, je lis tous les messages.',
      '',
      'Tes réponses m\'aident à adapter le contenu des 3 sessions pour qu\'elles répondent exactement à TES questions.',
      '',
      'On commence dans 6 jours — prépare-toi ! 🔥',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Variable {{1}} = champ "First Name" du contact Wati',
      'Délai d\'envoi : J-7 + 24 heures (1 jour après welcome_j7)',
      'Si le contact répond → le message entre dans la file de l\'agent IA (service ai_agent)',
    ],
  },
  {
    num: 3,
    key: 'challenge_day_1',
    name: 'Live Jour 1 — La méthode FBA de A à Z',
    step: 'DAY_1 (Jour J, 2h avant la session)',
    audience: 'Tous les inscrits actifs',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
      { var: '{{2}}', desc: 'URL de la session StreamYard (ex : https://streamyard.com/watch/xxxx)' },
      { var: '{{3}}', desc: 'Heure de la session (ex : 20h00)' },
    ],
    trigger: 'Webhook StreamYard déclenché 2h avant le live du Jour 1',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Rareté & Urgence + Present Bias',
    psychDesc: 'La Rareté (Scarcity) augmente la valeur perçue d\'un événement en soulignant son caractère unique et limité dans le temps. Combinée au Present Bias (agir maintenant), le sentiment d\'urgence pousse à rejoindre le live immédiatement plutôt que de remettre à plus tard. Le lien direct réduit le "coût d\'activation" (BJ Fogg).',
    message: [
      '🚨 {{1}}, c\'est MAINTENANT !',
      '',
      'Le Challenge Amazon FBA Jour 1 commence dans 2 heures à {{3}} !',
      '',
      '📹 Rejoins le live ici : {{2}}',
      '',
      'Au programme ce soir :',
      '✅ La méthode FBA expliquée simplement',
      '✅ Les erreurs à éviter absolument',
      '✅ Ton plan d\'action personnalisé',
      '',
      '⚡ Ce live n\'est PAS repassé — sois là !',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      '{{1}} = prénom | {{2}} = URL StreamYard du live | {{3}} = heure locale de début',
      'Déclencheur : POST /webhooks/streamyard/session avec { "session_day": 1, "stream_url": "..." }',
      'Envoi : 2 heures avant le live (configurable dans le service campaigns)',
    ],
  },
  {
    num: 4,
    key: 'challenge_day_2',
    name: 'Live Jour 2 — Pour ceux qui ont assisté à J1',
    step: 'DAY_2 (Jour J+1, 2h avant la session)',
    audience: 'Contacts ayant assisté au Jour 1 (score ≥ 1)',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
      { var: '{{2}}', desc: 'URL StreamYard Jour 2' },
      { var: '{{3}}', desc: 'Heure de la session' },
    ],
    trigger: 'Webhook StreamYard Jour 2 × filtre contacts avec score ≥ 1',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Effet Goal-Gradient (Progrès vers l\'objectif)',
    psychDesc: 'L\'effet Goal-Gradient (Hull, 1932 ; repris en marketing comportemental) montre que plus on est proche d\'un objectif, plus l\'effort et la motivation augmentent. En rappelant que le contact a déjà fait le premier pas et qu\'il lui en reste seulement 2 sur 3, on accélère naturellement son engagement vers le live du Jour 2.',
    message: [
      '🔥 {{1}}, tu as fait le premier pas !',
      '',
      'Tu étais là hier soir pour le Jour 1 — bravo, tu fais partie des gens qui passent à l\'action.',
      '',
      'Ce soir à {{3}}, on passe au niveau supérieur :',
      '→ Comment trouver TON produit gagnant',
      '→ Les outils pour analyser la demande',
      '→ Comment négocier avec les fournisseurs',
      '',
      '📹 Ton lien : {{2}}',
      '',
      '2 sessions sur 3 — tu es à mi-chemin de ta transformation. 💪',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Filtre d\'audience : contacts avec status_score ≥ 1 dans la DB (ont lu/vu le message J1)',
      '{{2}} = URL StreamYard Jour 2 | {{3}} = heure du live',
      'Ce template est distinct de challenge_day_2_catchup (Wati branch logic ou 2 broadcasts séparés)',
    ],
  },
  {
    num: 5,
    key: 'challenge_day_2_catchup',
    name: 'Rattrapage Jour 2 — Pour ceux qui ont manqué J1',
    step: 'DAY_2 (même soir, audience différente)',
    audience: 'Contacts N\'ayant PAS assisté au Jour 1',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
      { var: '{{2}}', desc: 'URL StreamYard Jour 2' },
      { var: '{{3}}', desc: 'Heure de la session' },
    ],
    trigger: 'Même webhook StreamYard Jour 2 × filtre contacts avec score = 0',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Aversion à la Perte Douce (Loss Aversion sans culpabilisation)',
    psychDesc: 'Kahneman & Tversky : les pertes pèsent 2× plus que les gains équivalents. Ce message active l\'aversion à la perte en soulignant ce qui a été manqué (sans culpabiliser) et en offrant une "deuxième chance". La formulation douce ("la vie, ça arrive") préserve la relation et réduit la résistance psychologique, tout en activant le FOMO.',
    message: [
      'Bonjour {{1}} 👋',
      '',
      'Hier soir, tu n\'as pas pu rejoindre le Jour 1 — la vie, ça arrive !',
      '',
      'La bonne nouvelle ? Ce soir à {{3}}, le Jour 2 est encore accessible et tu peux sauter directement dedans :',
      '',
      '→ Comment identifier un produit gagnant sur Amazon',
      '→ Les critères de sélection qui font la différence',
      '→ Les fournisseurs à privilégier',
      '',
      '📹 Rejoins-nous ce soir : {{2}}',
      '',
      'Ne manque pas cette session aussi — chaque live compte. 🎯',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Filtre d\'audience : contacts avec status_score = 0 (n\'ont pas interagi avec J1)',
      'Envoi simultané au template challenge_day_2, sur l\'audience inverse',
      'Ton volontairement empathique — pas de culpabilisation',
    ],
  },
  {
    num: 6,
    key: 'challenge_day_3',
    name: 'Live Jour 3 (Final) — Pour ceux présents à J2',
    step: 'DAY_3 (dernier jour du challenge, 2h avant)',
    audience: 'Contacts ayant assisté au Jour 2',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
      { var: '{{2}}', desc: 'URL StreamYard Jour 3 (Final)' },
      { var: '{{3}}', desc: 'Heure de la session finale' },
    ],
    trigger: 'Webhook StreamYard Jour 3 × filtre contacts engagés J2',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Règle du Pic et de la Fin (Peak-End Rule)',
    psychDesc: 'Kahneman : les gens jugent une expérience principalement sur son moment le plus intense (pic) et sa conclusion. En positionnant le Jour 3 comme "la révélation" et "la session la plus importante", on crée l\'anticipation d\'un pic mémorable. La mention du moment de lancement (l\'offre) ancre la fin comme une décision concrète — renforçant la mémorabilité positive de l\'ensemble du challenge.',
    message: [
      '🏆 {{1}} — ce soir, c\'est LA session !',
      '',
      'Tu as parcouru un sacré chemin depuis le Jour 1.',
      '',
      'Ce soir à {{3}}, la session finale :',
      '→ Comment lancer ton produit sur Amazon (les étapes exactes)',
      '→ La stratégie pour atteindre la rentabilité rapidement',
      '→ Et... une surprise pour ceux qui veulent aller plus loin 🎁',
      '',
      '📹 Ton lien final : {{2}}',
      '',
      'C\'est ce soir que tout se joue. Sois là ! 🔥',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Filtre : contacts ayant interagi positivement avec J2 (score ≥ 2)',
      'La "surprise" désigne le pitch de l\'offre de formation — adapter si besoin',
      '{{2}} = URL StreamYard Jour 3 | {{3}} = heure exacte',
    ],
  },
  {
    num: 7,
    key: 'challenge_day_3_catchup',
    name: 'Rattrapage Jour 3 — Pour ceux qui ont manqué J2',
    step: 'DAY_3 (même soir, audience différente)',
    audience: 'Contacts N\'ayant PAS assisté au Jour 2',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
      { var: '{{2}}', desc: 'URL StreamYard Jour 3' },
      { var: '{{3}}', desc: 'Heure de la session' },
    ],
    trigger: 'Même webhook Jour 3 × filtre contacts avec score faible',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Effet Zeigarnik + Comptabilité Mentale (Mental Accounting)',
    psychDesc: 'L\'effet Zeigarnik maintient les tâches inachevées dans la mémoire active — "le challenge n\'est pas fini". Le Mental Accounting (Thaler) rappelle qu\'ils ont déjà "investi" en s\'inscrivant : abandonner maintenant, c\'est perdre cet investissement. La dernière chance crée un ancrage de valeur résiduelle et reactive la motivation à clore l\'expérience positivement.',
    message: [
      'Bonjour {{1}} 😊',
      '',
      'Tu as manqué quelques sessions — mais le challenge n\'est pas terminé !',
      '',
      'Ce soir à {{3}}, la session FINALE est encore ouverte :',
      '→ Les étapes concrètes pour lancer sur Amazon',
      '→ Tout ce dont tu as besoin pour démarrer',
      '',
      'Tu t\'es inscrit(e) pour une raison. Ce soir, souviens-t\'en.',
      '',
      '📹 Rejoins-nous : {{2}}',
      '',
      'C\'est ta dernière chance dans ce challenge — ne la laisse pas passer. 💙',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Filtre : contacts avec score = 0 ou 1 (faible engagement J1/J2)',
      'Ton doux et motivant — pas de reproche, appel à l\'investissement initial',
      'La phrase "Tu t\'es inscrit(e) pour une raison" rappelle l\'intention d\'origine',
    ],
  },
  {
    num: 8,
    key: 'post_challenge_recap',
    name: 'Récap post-challenge — Pour les participants assidus',
    step: 'AFTER_1 (J+1, lendemain du Jour 3)',
    audience: 'Contacts ayant assisté au Jour 3 (les plus engagés)',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
    ],
    trigger: '24h après la fin du Jour 3 (webhook StreamYard de clôture)',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Réciprocité + Pied-dans-la-porte (Foot-in-the-Door)',
    psychDesc: 'La Réciprocité (Cialdini) : donner de la valeur (récap, ressources) crée une obligation morale de rendre. Combinée au Foot-in-the-Door, la progression naturelle petits engagements → grand engagement prépare le contact à l\'offre. On ne vend pas ici — on offre un récap précieux, ce qui rend le prochain message (offre) attendu et légitime.',
    message: [
      '🎉 {{1}}, bravo — tu l\'as fait !',
      '',
      'Tu as complété les 3 sessions du Challenge Amazon FBA. Peu de gens font ça.',
      '',
      'Voici ce que tu emportes de ce challenge :',
      '✅ La méthode FBA complète',
      '✅ Les critères de sélection d\'un produit gagnant',
      '✅ Les étapes de lancement sur Amazon',
      '',
      'La question maintenant : qu\'est-ce que tu fais de ça ?',
      '',
      'Je reviens vers toi dans 24h avec quelque chose qui t\'aidera à passer à l\'étape suivante. 🚀',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Filtre : contacts avec score ≥ 3 (présents aux 3 sessions)',
      'Pas de CTA de vente dans ce message — uniquement valeur + anticipation',
      'Le suivi J+2 (post_challenge_followup) portera l\'offre principale',
    ],
  },
  {
    num: 9,
    key: 'post_challenge_missed',
    name: 'Re-engagement post-challenge — Pour les absents au Jour 3',
    step: 'AFTER_1 (J+1, même timing, audience différente)',
    audience: 'Contacts N\'ayant PAS assisté au Jour 3',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
    ],
    trigger: '24h après la fin du Jour 3 × filtre contacts avec score < 3',
    category: 'MARKETING',
    language: 'fr',
    lever: 'FOMO + Ouverture (Porte entrouverte)',
    psychDesc: 'La Fear Of Missing Out (FOMO) activée par le résumé de ce qui a été manqué. Plutôt que de "fermer la porte", on maintient une "porte entrouverte" — une technique de maintien de relation qui préserve l\'option pour une prochaine cohorte ou l\'offre de rattrapage. Cela maintient le contact dans le pipeline sans créer de friction.',
    message: [
      'Bonjour {{1}} 👋',
      '',
      'La session finale du challenge s\'est terminée hier soir.',
      '',
      'Il y a eu des révélations importantes — notamment sur comment démarrer concrètement et accélérer les premiers résultats sur Amazon.',
      '',
      'Tu n\'as pas pu être là, et c\'est ok.',
      '',
      'Si tu veux quand même accéder aux informations présentées, dis-le-moi ici.',
      '',
      'Je reste disponible pour toi. 🙌',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Filtre : contacts avec score < 3 (n\'ont pas complété le Jour 3)',
      'Ton empathique, pas de pression — l\'objectif est de maintenir le lien',
      'Les réponses arrivent dans la file de l\'agent IA pour traitement personnalisé',
    ],
  },
  {
    num: 10,
    key: 'post_challenge_followup',
    name: 'Dernière chance — Suivi J+2 (tous les contacts)',
    step: 'AFTER_2 (J+2, 48h après la fin du Jour 3)',
    audience: 'Tous les contacts encore actifs dans la séquence',
    vars: [
      { var: '{{1}}', desc: 'Prénom du contact' },
    ],
    trigger: '48h après la fin du Jour 3 (tous contacts)',
    category: 'MARKETING',
    language: 'fr',
    lever: 'Dernière Chance Douce + Ancrage de Valeur',
    psychDesc: 'L\'ancrage de valeur (Anchoring) rappelle ce que le contact a déjà reçu gratuitement avant de présenter l\'offre payante. La "dernière chance douce" crée une urgence sans agressivité — une technique de clôture respectueuse qui préserve la relation à long terme même si le contact ne convertit pas maintenant. Le CTA simple ("Dis-moi") réduit la friction maximalement.',
    message: [
      '{{1}}, c\'est mon dernier message pour ce challenge. 😊',
      '',
      'En 3 sessions, tu as eu accès à des méthodes que d\'autres payent des centaines d\'euros pour apprendre.',
      '',
      'Si tu veux aller plus loin et être accompagné(e) pour lancer ton activité Amazon FBA de manière structurée — j\'ai quelque chose pour toi.',
      '',
      'Dis-moi "OUI" ici et je t\'envoie les détails.',
      '',
      'Quoi qu\'il arrive, merci d\'avoir été là. 🙏',
      '',
      'À bientôt,',
      'L\'équipe Challenge Amazon FBA',
    ],
    watiNotes: [
      'Catégorie : MARKETING | Langue : fr',
      'Envoi à TOUS les contacts restants dans la séquence (score = any)',
      'La réponse "OUI" déclenche l\'agent IA qui envoie le lien de l\'offre',
      'C\'est le dernier message automatique — après, passage en suivi manuel ou nouvelle campagne',
    ],
  },
];

// ─── DOCUMENT BUILDER ─────────────────────────────────────────────────────────
function buildDoc() {
  const children = [];

  // ── COVER PAGE ──────────────────────────────────────────────────────────────
  children.push(
    ...spacer(6),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'CHALLENGE AMAZON FBA', font: 'Arial', bold: true, size: 48, color: C.primaryDark })],
      spacing: { after: 120 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Séquence de Messages WhatsApp', font: 'Arial', size: 36, color: C.primary })],
      spacing: { after: 80 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Dossier de validation client', font: 'Arial', size: 24, color: C.gray400, italics: true })],
      spacing: { after: 400 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: '──────────────────────────────────', font: 'Arial', color: C.gray200 })],
      spacing: { after: 200 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Préparé par : Votre Agence / Équipe Technique', font: 'Arial', size: 20, color: C.gray700 })],
      spacing: { after: 80 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Date : Mai 2026', font: 'Arial', size: 20, color: C.gray700 })],
      spacing: { after: 80 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: 'Version : 1.0 — Pour validation', font: 'Arial', size: 20, color: C.warning, bold: true })],
    }),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── INTRODUCTION ─────────────────────────────────────────────────────────────
  children.push(
    sectionHeading('1. Présentation du projet', 1),
    new Paragraph({
      children: [run('Ce document présente les ', { size: 20 }), bold('10 modèles de messages WhatsApp', { size: 20 }), run(' conçus pour accompagner les participants du Challenge Amazon FBA, de leur inscription jusqu\'à J+2 après la dernière session.', { size: 20 })],
      spacing: { after: 120 },
    }),
    new Paragraph({
      children: [run('Chaque message a été rédigé en appliquant des ', { size: 20 }), bold('principes de psychologie comportementale', { size: 20, color: C.purple }), run(' (influence éthique, science du comportement) pour maximiser l\'engagement, la présence aux lives et la conversion.', { size: 20 })],
      spacing: { after: 200 },
    }),

    sectionHeading('Objectifs de la séquence', 2),
    ...['Maximiser le taux de présence à chaque session live (objectif : ≥ 60%)',
        'Maintenir l\'engagement des participants entre les sessions',
        'Réactiver les contacts peu engagés sans nuire à la relation',
        'Préparer le terrain pour la conversion à l\'offre de formation (J+2)',
    ].map(txt => new Paragraph({
      children: [run('• ' + txt, { size: 20, color: C.gray700 })],
      spacing: { before: 60, after: 0 },
      indent: { left: 360 },
    })),
    ...spacer(1),

    sectionHeading('Infrastructure technique', 2),
    new Paragraph({
      children: [run('Les messages sont envoyés via ', { size: 20 }), bold('Wati (WhatsApp Business API)', { size: 20 }), run(', connecté à une plateforme Node.js/FastAPI hébergée sur un VPS privé. La séquence est déclenchée automatiquement via :', { size: 20 })],
      spacing: { after: 120 },
    }),
    ...['Systeme.io → webhook d\'inscription → démarrage de la séquence J-7',
        'StreamYard → webhook de session → envoi des messages de rappel J1/J2/J3',
        'La plateforme calcule le score d\'engagement et filtre l\'audience automatiquement',
    ].map(txt => new Paragraph({
      children: [run('→ ' + txt, { size: 20, color: C.gray700 })],
      spacing: { before: 60, after: 0 },
      indent: { left: 360 },
    })),
    ...spacer(1),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── SEQUENCE OVERVIEW TABLE ───────────────────────────────────────────────────
  children.push(
    sectionHeading('2. Vue d\'ensemble de la séquence', 1),
    new Paragraph({
      children: [run('Le tableau ci-dessous résume les 10 messages, leur timing, l\'audience cible et le levier psychologique principal.', { size: 20, color: C.gray700 })],
      spacing: { after: 160 },
    }),
  );

  const headerRow = new TableRow({
    tableHeader: true,
    children: [
      ['#', 760], ['Clé Wati', 2200], ['Timing', 1200], ['Audience', 2000], ['Levier principal', 3200],
    ].map(([label, w]) => new TableCell({
      width: { size: w, type: WidthType.DXA },
      borders: cellBorder(C.primary),
      shading: { type: ShadingType.CLEAR, fill: C.primaryDark },
      margins: { top: 80, bottom: 80, left: 100, right: 100 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: label, font: 'Arial', bold: true, size: 18, color: C.white })],
      })],
    })),
  });

  const overviewRows = templates.map((t, i) => new TableRow({
    children: [
      [String(t.num), 760, AlignmentType.CENTER],
      [t.key, 2200, AlignmentType.LEFT],
      [t.step.split(' ')[0], 1200, AlignmentType.CENTER],
      [t.audience.length > 35 ? t.audience.substring(0, 35) + '…' : t.audience, 2000, AlignmentType.LEFT],
      [t.lever, 3200, AlignmentType.LEFT],
    ].map(([text, w, align]) => new TableCell({
      width: { size: w, type: WidthType.DXA },
      borders: cellBorder(C.gray200),
      shading: { type: ShadingType.CLEAR, fill: i % 2 === 0 ? C.white : C.lightGray },
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({
        alignment: align,
        children: [new TextRun({ text, font: 'Arial', size: 16, color: C.gray700 })],
      })],
    })),
  }));

  children.push(
    new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [760, 2200, 1200, 2000, 3200],
      rows: [headerRow, ...overviewRows],
    }),
    ...spacer(1),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── LEGEND ───────────────────────────────────────────────────────────────────
  children.push(
    sectionHeading('3. Légende des variables', 1),
    new Paragraph({
      children: [
        run('Les messages contiennent des ', { size: 20 }),
        bold('variables dynamiques', { size: 20, color: C.accent }),
        run(' remplacées automatiquement par Wati au moment de l\'envoi :', { size: 20 }),
      ],
      spacing: { after: 160 },
    }),
    new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [1440, 3000, 4920],
      rows: [
        new TableRow({
          tableHeader: true,
          children: [['Variable', 1440], ['Valeur injectée', 3000], ['Source', 4920]].map(([label, w]) =>
            new TableCell({
              width: { size: w, type: WidthType.DXA },
              borders: cellBorder(C.accent),
              shading: { type: ShadingType.CLEAR, fill: C.accentDark },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: label, font: 'Arial', bold: true, size: 18, color: C.white })] })],
            })
          ),
        }),
        ...([
          ['{{1}}', 'Prénom du contact', 'Champ contact Wati ("First Name") — vient de Systeme.io'],
          ['{{2}}', 'URL du live StreamYard', 'Webhook StreamYard → service campaigns → Wati'],
          ['{{3}}', 'Heure de la session', 'Webhook StreamYard (ex : "20h00") → formatée par le service'],
        ].map(([v, val, src], i) => new TableRow({
          children: [
            new TableCell({
              width: { size: 1440, type: WidthType.DXA },
              borders: cellBorder(C.gray200),
              shading: { type: ShadingType.CLEAR, fill: C.successBg },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: v, font: 'Arial', bold: true, size: 18, color: C.accent })] })],
            }),
            new TableCell({
              width: { size: 3000, type: WidthType.DXA },
              borders: cellBorder(C.gray200),
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: val, font: 'Arial', size: 18, color: C.black })] })],
            }),
            new TableCell({
              width: { size: 4920, type: WidthType.DXA },
              borders: cellBorder(C.gray200),
              shading: { type: ShadingType.CLEAR, fill: i % 2 === 0 ? C.white : C.lightGray },
              margins: { top: 80, bottom: 80, left: 120, right: 120 },
              children: [new Paragraph({ children: [new TextRun({ text: src, font: 'Arial', size: 16, color: C.gray700, italics: true })] })],
            }),
          ],
        }))),
      ],
    }),
    ...spacer(1),
    new Paragraph({ children: [new PageBreak()] }),
  );

  // ── TEMPLATES ─────────────────────────────────────────────────────────────────
  children.push(sectionHeading('4. Détail des 10 modèles de messages', 1));

  templates.forEach((t, idx) => {
    // Template header
    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: `Message ${t.num} / 10  —  `, font: 'Arial', size: 24, color: C.gray400 }),
          new TextRun({ text: t.name, font: 'Arial', bold: true, size: 28, color: C.primaryDark }),
        ],
        spacing: { before: 320, after: 80 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 3, color: C.primary, space: 4 } },
      }),
    );

    // Info table
    const infoRows = [
      ['🏷️  Clé Wati', t.key],
      ['📅 Timing', t.step],
      ['👥 Audience', t.audience],
      ['⚡ Déclencheur', t.trigger],
      ['📋 Catégorie Wati', `${t.category} | Langue : ${t.language}`],
    ];

    children.push(
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2200, 7160],
        rows: infoRows.flatMap(([label, value]) => labeledRow(label, value)),
      }),
      ...spacer(1),
    );

    // Variables table (if any)
    if (t.vars.length > 0) {
      children.push(
        new Paragraph({
          children: [bold('Variables du message', { size: 20, color: C.gray700 })],
          spacing: { before: 80, after: 80 },
        }),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1440, 7920],
          rows: [
            new TableRow({
              tableHeader: true,
              children: [
                new TableCell({
                  width: { size: 1440, type: WidthType.DXA },
                  borders: cellBorder(C.accent),
                  shading: { type: ShadingType.CLEAR, fill: C.accentDark },
                  margins: { top: 60, bottom: 60, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: 'Variable', font: 'Arial', bold: true, size: 18, color: C.white })] })],
                }),
                new TableCell({
                  width: { size: 7920, type: WidthType.DXA },
                  borders: cellBorder(C.accent),
                  shading: { type: ShadingType.CLEAR, fill: C.accentDark },
                  margins: { top: 60, bottom: 60, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: 'Description / Valeur attendue', font: 'Arial', bold: true, size: 18, color: C.white })] })],
                }),
              ],
            }),
            ...t.vars.map(v => new TableRow({
              children: [
                new TableCell({
                  width: { size: 1440, type: WidthType.DXA },
                  borders: cellBorder(C.gray200),
                  shading: { type: ShadingType.CLEAR, fill: C.successBg },
                  margins: { top: 60, bottom: 60, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: v.var, font: 'Arial', bold: true, size: 18, color: C.accent })] })],
                }),
                new TableCell({
                  width: { size: 7920, type: WidthType.DXA },
                  borders: cellBorder(C.gray200),
                  margins: { top: 60, bottom: 60, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: v.desc, font: 'Arial', size: 18, color: C.black })] })],
                }),
              ],
            })),
          ],
        }),
        ...spacer(1),
      );
    }

    // Psych lever box
    children.push(
      psychBox(t.lever, t.psychDesc),
      ...spacer(1),
    );

    // Message text
    children.push(
      new Paragraph({
        children: [bold('💬  Texte du message WhatsApp', { size: 20, color: C.gray700 })],
        spacing: { before: 80, after: 80 },
      }),
      messageBox(t.message),
      ...spacer(1),
    );

    // Wati notes
    children.push(
      watiBox(t.watiNotes),
    );

    // Page break between templates (not after last)
    if (idx < templates.length - 1) {
      children.push(new Paragraph({ children: [new PageBreak()] }));
    }
  });

  // ── NEXT STEPS ────────────────────────────────────────────────────────────────
  children.push(
    new Paragraph({ children: [new PageBreak()] }),
    sectionHeading('5. Étapes de validation et de mise en ligne', 1),

    sectionHeading('Étape 1 — Validation du client (ce document)', 2),
    ...['Lire chaque message et valider le texte, le ton et les variables',
        'Vérifier que les leviers psychologiques correspondent à l\'identité de marque',
        'Annoter les corrections souhaitées directement dans ce document',
        'Retourner le document validé pour procéder à l\'étape 2',
    ].map((txt, i) => new Paragraph({
      children: [
        new TextRun({ text: `${i + 1}. `, font: 'Arial', bold: true, size: 20, color: C.primary }),
        new TextRun({ text: txt, font: 'Arial', size: 20, color: C.black }),
      ],
      spacing: { before: 80, after: 0 },
      indent: { left: 360 },
    })),
    ...spacer(1),

    sectionHeading('Étape 2 — Création des templates dans Wati', 2),
    ...['Se connecter à https://app.wati.io → Template Messages → Add New Template',
        'Pour chaque template : saisir la Clé Wati (champ "Template Name"), sélectionner Catégorie MARKETING, Langue Français (fr)',
        'Copier-coller le texte du message en remplaçant les variables {{1}}, {{2}}, {{3}} par les champs Wati',
        'Soumettre chaque template pour approbation Meta (WhatsApp)',
    ].map((txt, i) => new Paragraph({
      children: [
        new TextRun({ text: `${i + 1}. `, font: 'Arial', bold: true, size: 20, color: C.warning }),
        new TextRun({ text: txt, font: 'Arial', size: 20, color: C.black }),
      ],
      spacing: { before: 80, after: 0 },
      indent: { left: 360 },
    })),
    ...spacer(1),

    new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [9360],
      rows: [new TableRow({
        children: [new TableCell({
          width: { size: 9360, type: WidthType.DXA },
          borders: {
            top:    { style: BorderStyle.SINGLE, size: 2, color: C.warning },
            bottom: { style: BorderStyle.SINGLE, size: 2, color: C.warning },
            left:   { style: BorderStyle.THICK,  size: 12, color: C.warning },
            right:  { style: BorderStyle.SINGLE, size: 2, color: C.warning },
          },
          shading: { type: ShadingType.CLEAR, fill: C.warningBg },
          margins: { top: 100, bottom: 100, left: 200, right: 200 },
          children: [
            new Paragraph({
              children: [new TextRun({ text: '⏱️  Délai d\'approbation Meta', font: 'Arial', bold: true, size: 18, color: C.warning })],
              spacing: { after: 60 },
            }),
            new Paragraph({
              children: [new TextRun({ text: 'Les templates WhatsApp MARKETING nécessitent une approbation de Meta (WhatsApp) avant d\'être utilisables. Ce processus prend généralement 24 à 72 heures. Soumettez les templates dès que le client a validé ce document.', font: 'Arial', size: 18, color: C.gray700 })],
            }),
          ],
        })],
      })],
    }),
    ...spacer(1),

    sectionHeading('Étape 3 — Test et mise en production', 2),
    ...['Tester chaque template sur un numéro de test Wati avant le launch',
        'Vérifier que les variables sont bien remplacées par les bonnes valeurs',
        'Configurer les automations dans Systeme.io et StreamYard (webhooks)',
        'Faire un "dry run" avec 2-3 contacts test pour valider le flux complet',
        'Lancement officiel : activer la campagne pour le prochain challenge',
    ].map((txt, i) => new Paragraph({
      children: [
        new TextRun({ text: `${i + 1}. `, font: 'Arial', bold: true, size: 20, color: C.accent }),
        new TextRun({ text: txt, font: 'Arial', size: 20, color: C.black }),
      ],
      spacing: { before: 80, after: 0 },
      indent: { left: 360 },
    })),
    ...spacer(2),

    // Footer note
    new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [9360],
      rows: [new TableRow({
        children: [new TableCell({
          width: { size: 9360, type: WidthType.DXA },
          borders: cellBorder(C.gray200),
          shading: { type: ShadingType.CLEAR, fill: C.lightGray },
          margins: { top: 120, bottom: 120, left: 240, right: 240 },
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ text: 'Document confidentiel — Pour validation client uniquement', font: 'Arial', bold: true, size: 18, color: C.gray700 })],
              spacing: { after: 60 },
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [new TextRun({ text: 'Ce document est préparé par votre équipe technique. Tous les messages sont rédigés selon les meilleures pratiques de marketing WhatsApp et de psychologie comportementale éthique.', font: 'Arial', size: 16, color: C.gray400, italics: true })],
            }),
          ],
        })],
      })],
    }),
  );

  // ─── ASSEMBLE DOCUMENT ────────────────────────────────────────────────────────
  return new Document({
    styles: {
      default: {
        document: { run: { font: 'Arial', size: 20, color: C.black } },
      },
      paragraphStyles: [
        {
          id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 32, bold: true, font: 'Arial', color: C.primaryDark },
          paragraph: { spacing: { before: 400, after: 160 }, outlineLevel: 0 },
        },
        {
          id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 26, bold: true, font: 'Arial', color: C.primary },
          paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 },
        },
        {
          id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 22, bold: true, font: 'Arial', color: C.gray700 },
          paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 },
        },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              children: [
                new TextRun({ text: 'Challenge Amazon FBA — Séquence WhatsApp', font: 'Arial', size: 16, color: C.gray400 }),
                new TextRun({ text: '\t', font: 'Arial' }),
                new TextRun({ text: 'CONFIDENTIEL', font: 'Arial', size: 16, bold: true, color: C.warning }),
              ],
              tabStops: [{ type: 'right', position: 9360 }],
            }),
            new Paragraph({
              border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: C.gray200, space: 1 } },
              children: [],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              border: { top: { style: BorderStyle.SINGLE, size: 1, color: C.gray200, space: 1 } },
              children: [
                new TextRun({ text: 'Pour validation client — Version 1.0 — Mai 2026', font: 'Arial', size: 16, color: C.gray400 }),
                new TextRun({ text: '\t', font: 'Arial' }),
                new TextRun({ text: 'Page ', font: 'Arial', size: 16, color: C.gray400 }),
                new TextRun({ text: '', font: 'Arial', size: 16, color: C.gray400, children: [PageNumber.CURRENT] }),
              ],
              tabStops: [{ type: 'right', position: 9360 }],
            }),
          ],
        }),
      },
      children,
    }],
  });
}

// ─── GENERATE FILE ────────────────────────────────────────────────────────────
const outputPath = path.join(__dirname, 'messages-challenge-amazon-fba.docx');
const doc = buildDoc();

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  const size = (buffer.length / 1024).toFixed(1);
  console.log(`✅  Document généré : ${outputPath}`);
  console.log(`📄  Taille : ${size} KB`);
  console.log(`📊  Templates inclus : ${templates.length}`);
}).catch(err => {
  console.error('❌  Erreur lors de la génération :', err.message);
  process.exit(1);
});
