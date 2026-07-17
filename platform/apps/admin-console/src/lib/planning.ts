// Journey constants extracted from StreamyardOpsPage for testability.

export const TEMPLATE_LABELS: Record<string, string> = {
  welcome_v1:                       "Bienvenue dans le challenge",
  countdown_j1_v1:                  "Compte à rebours J-1",
  live_day1_v1:                     "Broadcast J1 + lien StreamYard",
  live_day2_attended_v1:            "J2 — A assisté au live J1 ✅",
  live_day2_registered_absent_v1:   "J2 — Inscrit StreamYard mais absent J1 ⚠️",
  live_day2_not_registered_v1:      "J2 — Pas inscrit sur StreamYard J1 ❌",
  live_day3_attended_v1:            "J3 — A assisté au live J2 ✅",
  live_day3_registered_absent_v1:   "J3 — Inscrit StreamYard mais absent J2 ⚠️",
  live_day3_not_registered_v1:      "J3 — Pas inscrit sur StreamYard J2 ❌",
  live_day1_h10_v1:                 "H-10 J1 — Rappel 10 min avant le live",
  live_day2_h10_v1:                 "H-10 J2 — Rappel 10 min avant le live",
  live_day3_h2_v1:                  "H-2 J3 — Rappel 2h avant le live",
  live_day3_h10_v1:                 "H-10 J3 — Rappel 10 min avant le live",
  live_day3_h90_v1:                 "H+90 J3 — Offre commerciale (MARKETING)",
  post_replay_v1:                   "Replay J+1 — Lien replay 48h (MARKETING)",
  post_testimonials_v1:             "Reservation closer / echange (MARKETING)",
  post_closer_v1:                   "Dernier message avant appel closer (MARKETING)",
  post_closer_call_v1:              "Appel closer (lien réservation) (MARKETING)",
};

export const TEMPLATE_VARS: Record<string, string> = {
  welcome_v1:                       "{{1}}=prénom",
  countdown_j1_v1:                  "{{1}}=prénom, {{2}}=lien StreamYard J1, {{3}}=heure live",
  live_day1_v1:                     "{{1}}=prénom, {{2}}=lien StreamYard J1, {{3}}=heure live",
  live_day2_attended_v1:            "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day2_registered_absent_v1:   "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day2_not_registered_v1:      "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day3_attended_v1:            "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day3_registered_absent_v1:   "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day3_not_registered_v1:      "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day1_h10_v1:                 "{{1}}=prénom, {{2}}=lien StreamYard J1",
  live_day2_h10_v1:                 "{{1}}=prénom, {{2}}=lien StreamYard J2",
  live_day3_h2_v1:                  "{{1}}=prénom, {{2}}=lien StreamYard J3",
  live_day3_h10_v1:                 "{{1}}=prénom, {{2}}=lien StreamYard J3",
  live_day3_h90_v1:                 "{{1}}=prénom, {{2}}=lien offre paiement",
  post_replay_v1:                   "{{1}}=prénom, {{2}}=lien replay J3",
  post_testimonials_v1:             "{{1}}=prenom, {{2}}=lien reservation closer",
  post_closer_v1:                   "{{1}}=prénom, {{2}}=lien réservation closer",
  post_closer_call_v1:              "{{1}}=prénom, {{2}}=lien réservation closer",
};

export interface PlanningStep {
  step: string;
  dayOffset: number;
  phase: "countdown" | "live" | "post";
  phaseColor: string;
  label: string;
  templates: string[];
  timed?: boolean;
}

export const PLANNING_STEPS: PlanningStep[] = [
  { step: "WELCOME",       dayOffset: -999, phase: "countdown", phaseColor: "blue",    label: "Bienvenue (immédiat)",    templates: ["welcome_v1"] },
  { step: "COUNTDOWN_J1",  dayOffset: -1,   phase: "countdown", phaseColor: "blue",    label: "Compte à rebours J-1",    templates: ["countdown_j1_v1"] },
  { step: "DAY_1",         dayOffset: 0,    phase: "live",      phaseColor: "emerald", label: "Jour 1 — Live",           templates: ["live_day1_v1", "live_day1_h10_v1"], timed: true },
  { step: "DAY_2",         dayOffset: 1,    phase: "live",      phaseColor: "emerald", label: "Jour 2 — Live",           templates: ["live_day2_attended_v1", "live_day2_registered_absent_v1", "live_day2_not_registered_v1", "live_day2_h10_v1"], timed: true },
  { step: "DAY_3",         dayOffset: 2,    phase: "live",      phaseColor: "emerald", label: "Jour 3 — Live",           templates: ["live_day3_attended_v1", "live_day3_registered_absent_v1", "live_day3_not_registered_v1", "live_day3_h2_v1", "live_day3_h10_v1", "live_day3_h90_v1"], timed: true },
  { step: "AFTER_REPLAY",  dayOffset: 3,    phase: "post",      phaseColor: "amber",   label: "Replay J+1",              templates: ["post_replay_v1"] },
  { step: "AFTER_1",       dayOffset: 4,    phase: "post",      phaseColor: "amber",   label: "Reservation closer J+2",  templates: ["post_testimonials_v1"] },
  { step: "AFTER_2",       dayOffset: 5,    phase: "post",      phaseColor: "amber",   label: "Pré-closer J+3",          templates: ["post_closer_v1"] },
  { step: "AFTER_3",       dayOffset: 6,    phase: "post",      phaseColor: "amber",   label: "Appel closer J+4",        templates: ["post_closer_call_v1"] },
];

export interface JourneyTemplate {
  key: string;
  step: string;
  label: string;
  vars: string;
}

export interface JourneyPhase {
  phase: string;
  color: string;
  templates: JourneyTemplate[];
}

export const JOURNEY_PHASES: JourneyPhase[] = [
  {
    phase: "Phase 1 — Pré-challenge (J-1)",
    color: "blue",
    templates: [
      { key: "welcome_v1",       step: "WELCOME",       label: "Message de bienvenue",  vars: "{{1}} prénom" },
      { key: "countdown_j1_v1",  step: "COUNTDOWN J-1", label: "Compte à rebours J-1",  vars: "{{1}} prénom · {{2}} lien StreamYard · {{3}} heure" },
    ],
  },
  {
    phase: "Phase 2 — Jour 1",
    color: "emerald",
    templates: [
      { key: "live_day1_v1",     step: "DAY 1 — Matin", label: "Broadcast matin J1",   vars: "{{1}} prénom · {{2}} lien StreamYard · {{3}} heure" },
      { key: "live_day1_h10_v1", step: "DAY 1 — H-10",  label: "Rappel H-10 min",      vars: "{{1}} prénom · {{2}} lien StreamYard" },
    ],
  },
  {
    phase: "Phase 3 — Jour 2",
    color: "emerald",
    templates: [
      { key: "live_day2_attended_v1",          step: "DAY 2a — Matin", label: "A assisté J1",      vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day2_registered_absent_v1", step: "DAY 2b — Matin", label: "Inscrit absent J1", vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day2_not_registered_v1",    step: "DAY 2c — Matin", label: "Non inscrit J1",    vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day2_h10_v1",               step: "DAY 2 — H-10",   label: "Rappel H-10 min",   vars: "{{1}} prénom · {{2}} lien StreamYard" },
    ],
  },
  {
    phase: "Phase 4 — Jour 3",
    color: "orange",
    templates: [
      { key: "live_day3_attended_v1",          step: "DAY 3a — Matin", label: "A assisté J2",      vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day3_registered_absent_v1", step: "DAY 3b — Matin", label: "Inscrit absent J2", vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day3_not_registered_v1",    step: "DAY 3c — Matin", label: "Non inscrit J2",    vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day3_h2_v1",                step: "DAY 3 — H-2",    label: "Rappel H-2h",       vars: "{{1}} prénom · {{2}} lien StreamYard" },
      { key: "live_day3_h10_v1",               step: "DAY 3 — H-10",   label: "Rappel H-10 min",   vars: "{{1}} prénom · {{2}} lien StreamYard" },
      { key: "live_day3_h90_v1",               step: "DAY 3 — H+90",   label: "Offre H+90 (MARKETING)", vars: "{{1}} prénom · {{2}} lien offre paiement" },
    ],
  },
  {
    phase: "Phase 5 — Post-challenge",
    color: "purple",
    templates: [
      { key: "post_replay_v1",       step: "AFTER REPLAY — J+1", label: "Replay 48h (MARKETING)",        vars: "{{1}} prénom · {{2}} lien replay J3" },
      { key: "post_testimonials_v1", step: "AFTER 1 — J+2",      label: "Réservation / échange (MARKETING)",        vars: "{{1}} prénom · {{2}} lien réservation closer" },
      { key: "post_closer_v1",       step: "AFTER 2 — J+3",      label: "Pré-closer (MARKETING)",         vars: "{{1}} prénom · {{2}} lien réservation closer" },
      { key: "post_closer_call_v1",  step: "AFTER 3 — J+4",      label: "Appel closer (MARKETING)",       vars: "{{1}} prénom · {{2}} lien réservation closer" },
    ],
  },
];
