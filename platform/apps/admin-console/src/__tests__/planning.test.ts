import { describe, it, expect } from "vitest";
import {
  TEMPLATE_LABELS,
  TEMPLATE_VARS,
  PLANNING_STEPS,
  JOURNEY_PHASES,
} from "../lib/planning";

// ── Expected v6 template catalog ─────────────────────────────────────────────

const EXPECTED_KEYS = [
  "welcome_v6",
  "countdown_j1_v6",
  "live_day1_v6",
  "live_day1_h10_v6",
  "live_day2_attended_v6",
  "live_day2_registered_absent_v6",
  "live_day2_not_registered_v6",
  "live_day2_h10_v6",
  "live_day3_attended_v6",
  "live_day3_registered_absent_v6",
  "live_day3_not_registered_v6",
  "live_day3_h2_v6",
  "live_day3_h10_v6",
  "live_day3_h90_v6",
  "post_replay_v6",
  "post_testimonials_v6",
  "post_closer_v6",
  "post_closer_call_v6",
] as const;

// ── TEMPLATE_LABELS ───────────────────────────────────────────────────────────

describe("TEMPLATE_LABELS", () => {
  it("contains exactly 18 entries", () => {
    expect(Object.keys(TEMPLATE_LABELS)).toHaveLength(18);
  });

  it("all keys end with _v6", () => {
    for (const key of Object.keys(TEMPLATE_LABELS)) {
      expect(key, `${key} should end with _v6`).toMatch(/_v6$/);
    }
  });

  it("covers every expected template key", () => {
    for (const key of EXPECTED_KEYS) {
      expect(TEMPLATE_LABELS, `missing label for ${key}`).toHaveProperty(key);
    }
  });

  it("has no old _v2/_v3/_v4/_v5 keys", () => {
    for (const key of Object.keys(TEMPLATE_LABELS)) {
      expect(key).not.toMatch(/_v[2345](_utility)?$/);
    }
  });

  it("no empty labels", () => {
    for (const [key, label] of Object.entries(TEMPLATE_LABELS)) {
      expect(label.trim(), `empty label for ${key}`).not.toBe("");
    }
  });
});

// ── TEMPLATE_VARS ─────────────────────────────────────────────────────────────

describe("TEMPLATE_VARS", () => {
  it("has the same keys as TEMPLATE_LABELS", () => {
    expect(Object.keys(TEMPLATE_VARS).sort()).toEqual(
      Object.keys(TEMPLATE_LABELS).sort()
    );
  });

  it("all variables start with {{1}}", () => {
    for (const [key, vars] of Object.entries(TEMPLATE_VARS)) {
      expect(vars, `${key} should declare {{1}}`).toContain("{{1}}");
    }
  });

  it("broadcast and reminder templates have {{2}}", () => {
    const keysWithTwo = [
      "countdown_j1_v6",
      "live_day1_v6", "live_day2_attended_v6", "live_day2_registered_absent_v6",
      "live_day2_not_registered_v6", "live_day3_attended_v6",
      "live_day3_registered_absent_v6", "live_day3_not_registered_v6",
      "live_day1_h10_v6", "live_day2_h10_v6", "live_day3_h2_v6", "live_day3_h10_v6",
      "live_day3_h90_v6",
      "post_replay_v6", "post_testimonials_v6", "post_closer_v6", "post_closer_call_v6",
    ];
    for (const key of keysWithTwo) {
      expect(TEMPLATE_VARS[key], `${key} should declare {{2}}`).toContain("{{2}}");
    }
  });

  it("broadcast templates for day1/2/3 have {{3}} for heure", () => {
    const keysWithThree = [
      "countdown_j1_v6",
      "live_day1_v6",
      "live_day2_attended_v6", "live_day2_registered_absent_v6", "live_day2_not_registered_v6",
      "live_day3_attended_v6", "live_day3_registered_absent_v6", "live_day3_not_registered_v6",
    ];
    for (const key of keysWithThree) {
      expect(TEMPLATE_VARS[key], `${key} should declare {{3}}`).toContain("{{3}}");
    }
  });

  it("welcome_v6 only uses {{1}} (no URL or time)", () => {
    expect(TEMPLATE_VARS["welcome_v6"]).not.toContain("{{2}}");
  });
});

// ── PLANNING_STEPS ────────────────────────────────────────────────────────────

describe("PLANNING_STEPS", () => {
  it("has exactly 9 steps", () => {
    expect(PLANNING_STEPS).toHaveLength(9);
  });

  it("step keys are the 9 expected ones in order", () => {
    expect(PLANNING_STEPS.map((s) => s.step)).toEqual([
      "WELCOME",
      "COUNTDOWN_J1",
      "DAY_1",
      "DAY_2",
      "DAY_3",
      "AFTER_REPLAY",
      "AFTER_1",
      "AFTER_2",
      "AFTER_3",
    ]);
  });

  it("all template references end with _v6", () => {
    for (const step of PLANNING_STEPS) {
      for (const tpl of step.templates) {
        expect(tpl, `step ${step.step} has non-v6 template ${tpl}`).toMatch(/_v6$/);
      }
    }
  });

  it("no step references old _v2/_v3/_v4/_v5 templates", () => {
    for (const step of PLANNING_STEPS) {
      for (const tpl of step.templates) {
        expect(tpl).not.toMatch(/_v[2345](_utility)?$/);
      }
    }
  });

  it("WELCOME has dayOffset -999 (sent immediately on enroll)", () => {
    const welcome = PLANNING_STEPS.find((s) => s.step === "WELCOME")!;
    expect(welcome.dayOffset).toBe(-999);
  });

  it("COUNTDOWN_J1 is the only countdown step", () => {
    const countdowns = PLANNING_STEPS.filter((s) => s.phase === "countdown");
    expect(countdowns.map((s) => s.step)).toEqual(["WELCOME", "COUNTDOWN_J1"]);
  });

  it("live steps (DAY_1/2/3) are flagged as timed", () => {
    const liveSteps = PLANNING_STEPS.filter((s) => s.phase === "live");
    expect(liveSteps).toHaveLength(3);
    for (const step of liveSteps) {
      expect(step.timed, `${step.step} should be timed`).toBe(true);
    }
  });

  it("post steps (AFTER_REPLAY/1/2/3) are not timed", () => {
    const postSteps = PLANNING_STEPS.filter((s) => s.phase === "post");
    expect(postSteps).toHaveLength(4);
    for (const step of postSteps) {
      expect(step.timed).toBeFalsy();
    }
  });

  it("day offsets are sequential 0/1/2 for live days", () => {
    const live = PLANNING_STEPS.filter((s) => s.phase === "live");
    expect(live.map((s) => s.dayOffset)).toEqual([0, 1, 2]);
  });

  it("DAY_3 includes h2_v6, h10_v6 and h90_v6 timed templates", () => {
    const day3 = PLANNING_STEPS.find((s) => s.step === "DAY_3")!;
    expect(day3.templates).toContain("live_day3_h2_v6");
    expect(day3.templates).toContain("live_day3_h10_v6");
    expect(day3.templates).toContain("live_day3_h90_v6");
  });

  it("all template refs are defined in TEMPLATE_LABELS", () => {
    for (const step of PLANNING_STEPS) {
      for (const tpl of step.templates) {
        expect(TEMPLATE_LABELS, `${tpl} referenced in PLANNING_STEPS but missing from TEMPLATE_LABELS`).toHaveProperty(tpl);
      }
    }
  });
});

// ── JOURNEY_PHASES ────────────────────────────────────────────────────────────

describe("JOURNEY_PHASES", () => {
  const allPhaseTpls = JOURNEY_PHASES.flatMap((p) => p.templates);

  it("has exactly 5 phases", () => {
    expect(JOURNEY_PHASES).toHaveLength(5);
  });

  it("totals 18 templates across all phases", () => {
    expect(allPhaseTpls).toHaveLength(18);
  });

  it("all template keys end with _v6", () => {
    for (const tpl of allPhaseTpls) {
      expect(tpl.key, `${tpl.key} should end with _v6`).toMatch(/_v6$/);
    }
  });

  it("no duplicate template keys across phases", () => {
    const keys = allPhaseTpls.map((t) => t.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("covers the same 18 keys as TEMPLATE_LABELS", () => {
    const phaseKeys = new Set(allPhaseTpls.map((t) => t.key));
    const labelKeys = new Set(Object.keys(TEMPLATE_LABELS));
    expect(phaseKeys).toEqual(labelKeys);
  });

  it("each template has a non-empty label and vars", () => {
    for (const tpl of allPhaseTpls) {
      expect(tpl.label.trim(), `empty label for ${tpl.key}`).not.toBe("");
      expect(tpl.vars.trim(), `empty vars for ${tpl.key}`).not.toBe("");
    }
  });

  it("Phase 1 contains welcome and countdown only", () => {
    const phase1 = JOURNEY_PHASES[0];
    expect(phase1.templates.map((t) => t.key)).toEqual([
      "welcome_v6",
      "countdown_j1_v6",
    ]);
  });

  it("Phase 4 (Day 3) has 6 templates including h2_v6 and h90_v6", () => {
    const phase4 = JOURNEY_PHASES[3];
    expect(phase4.templates).toHaveLength(6);
    expect(phase4.templates.map((t) => t.key)).toContain("live_day3_h2_v6");
    expect(phase4.templates.map((t) => t.key)).toContain("live_day3_h90_v6");
  });

  it("Phase 5 (post) contains 4 templates including replay and closer", () => {
    const phase5 = JOURNEY_PHASES[4];
    expect(phase5.templates).toHaveLength(4);
    expect(phase5.templates.map((t) => t.key)).toEqual([
      "post_replay_v6",
      "post_testimonials_v6",
      "post_closer_v6",
      "post_closer_call_v6",
    ]);
  });
});
