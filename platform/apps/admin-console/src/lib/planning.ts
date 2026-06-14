// Journey constants extracted from StreamyardOpsPage for testability.

export const TEMPLATE_LABELS: Record<string, string> = {
  welcome_v5:                      "Bienvenue dans le challenge",
  countdown_j1_v5:                 "Compte à rebours J-1",
  live_day1_v5:                    "Broadcast J1 + lien StreamYard",
  live_day2_attended_v5:           "J2 — A assisté au live J1 ✅",
  live_day2_registered_absent_v5:  "J2 — Inscrit StreamYard mais absent J1 ⚠️",
  live_day2_not_registered_v5:     "J2 — Pas inscrit sur StreamYard J1 ❌",
  live_day3_attended_v5:           "J3 — A assisté au live J2 ✅",
  live_day3_registered_absent_v5:  "J3 — Inscrit StreamYard mais absent J2 ⚠️",
  live_day3_not_registered_v5:     "J3 — Pas inscrit sur StreamYard J2 ❌",
  live_day1_h10_v5:                "H-10 J1 — Rappel 10 min avant le live",
  live_day2_h10_v5:                "H-10 J2 — Rappel 10 min avant le live",
  live_day3_h10_v5:                "H-10 J3 — Rappel 10 min avant le live",
  post_testimonials_v5:            "Témoignages (lien page)",
  post_closer_call_v5:             "Appel closer (lien réservation)",
};

export const TEMPLATE_VARS: Record<string, string> = {
  welcome_v5:                      "{{1}}=prénom",
  countdown_j1_v5:                 "{{1}}=prénom, {{2}}=heure live",
  live_day1_v5:                    "{{1}}=prénom, {{2}}=lien StreamYard J1, {{3}}=heure live",
  live_day2_attended_v5:           "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day2_registered_absent_v5:  "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day2_not_registered_v5:     "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day3_attended_v5:           "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day3_registered_absent_v5:  "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day3_not_registered_v5:     "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day1_h10_v5:                "{{1}}=prénom, {{2}}=lien StreamYard J1",
  live_day2_h10_v5:                "{{1}}=prénom, {{2}}=lien StreamYard J2",
  live_day3_h10_v5:                "{{1}}=prénom, {{2}}=lien StreamYard J3",
  post_testimonials_v5:            "{{1}}=prénom, {{2}}=lien page témoignages",
  post_closer_call_v5:             "{{1}}=prénom, {{2}}=lien réservation closer",
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
  { step: "WELCOME",      dayOffset: -999, phase: "countdown", phaseColor: "blue",    label: "Bienvenue (immédiat)",   templates: ["welcome_v5"] },
  { step: "COUNTDOWN_J1", dayOffset: -1,   phase: "countdown", phaseColor: "blue",    label: "Compte à rebours J-1",   templates: ["countdown_j1_v5"] },
  { step: "DAY_1",        dayOffset: 0,    phase: "live",      phaseColor: "emerald", label: "Jour 1 — Live",          templates: ["live_day1_v5", "live_day1_h10_v5"], timed: true },
  { step: "DAY_2",        dayOffset: 1,    phase: "live",      phaseColor: "emerald", label: "Jour 2 — Live",          templates: ["live_day2_attended_v5", "live_day2_registered_absent_v5", "live_day2_not_registered_v5", "live_day2_h10_v5"], timed: true },
  { step: "DAY_3",        dayOffset: 2,    phase: "live",      phaseColor: "emerald", label: "Jour 3 — Live",          templates: ["live_day3_attended_v5", "live_day3_registered_absent_v5", "live_day3_not_registered_v5", "live_day3_h10_v5"], timed: true },
  { step: "AFTER_1",      dayOffset: 3,    phase: "post",      phaseColor: "amber",   label: "Témoignages J+3",        templates: ["post_testimonials_v5"] },
  { step: "AFTER_2",      dayOffset: 4,    phase: "post",      phaseColor: "amber",   label: "Appel closer J+4",       templates: ["post_closer_call_v5"] },
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
      { key: "welcome_v5",      step: "WELCOME",       label: "Message de bienvenue",  vars: "{{1}} prénom" },
      { key: "countdown_j1_v5", step: "COUNTDOWN J-1", label: "Compte à rebours J-1",  vars: "{{1}} prénom · {{2}} heure" },
    ],
  },
  {
    phase: "Phase 2 — Jour 1",
    color: "emerald",
    templates: [
      { key: "live_day1_v5",     step: "DAY 1 — Matin", label: "Broadcast matin J1",   vars: "{{1}} prénom · {{2}} lien StreamYard · {{3}} heure" },
      { key: "live_day1_h10_v5", step: "DAY 1 — H-10",  label: "Rappel H-10 min",      vars: "{{1}} prénom · {{2}} lien StreamYard" },
    ],
  },
  {
    phase: "Phase 3 — Jour 2",
    color: "emerald",
    templates: [
      { key: "live_day2_attended_v5",          step: "DAY 2a — Matin", label: "A assisté J1",      vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day2_registered_absent_v5", step: "DAY 2b — Matin", label: "Inscrit absent J1", vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day2_not_registered_v5",    step: "DAY 2c — Matin", label: "Non inscrit J1",    vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day2_h10_v5",               step: "DAY 2 — H-10",   label: "Rappel H-10 min",   vars: "{{1}} prénom · {{2}} lien StreamYard" },
    ],
  },
  {
    phase: "Phase 4 — Jour 3",
    color: "orange",
    templates: [
      { key: "live_day3_attended_v5",          step: "DAY 3a — Matin", label: "A assisté J2",      vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day3_registered_absent_v5", step: "DAY 3b — Matin", label: "Inscrit absent J2", vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day3_not_registered_v5",    step: "DAY 3c — Matin", label: "Non inscrit J2",    vars: "{{1}} prénom · {{2}} lien · {{3}} heure" },
      { key: "live_day3_h10_v5",               step: "DAY 3 — H-10",   label: "Rappel H-10 min",   vars: "{{1}} prénom · {{2}} lien StreamYard" },
    ],
  },
  {
    phase: "Phase 5 — Post-challenge",
    color: "purple",
    templates: [
      { key: "post_testimonials_v5", step: "AFTER 1 — J+3", label: "Témoignages",  vars: "{{1}} prénom · {{2}} lien page témoignages" },
      { key: "post_closer_call_v5",  step: "AFTER 2 — J+4", label: "Appel closer", vars: "{{1}} prénom · {{2}} lien réservation closer" },
    ],
  },
];
