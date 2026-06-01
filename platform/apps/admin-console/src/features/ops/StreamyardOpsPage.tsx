import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  CalendarCheck,
  CheckCircle,
  Clock,
  Eye,
  Link,
  ListChecks,
  UploadSimple,
  Users,
  WarningCircle,
  ArrowClockwise,
  Robot,
  Play,
  Power,
  ChartBar,
  ChatCircle,
  Info,
  BookOpen,
  CaretDown,
  CaretUp,
  Broadcast,
  Brain,
  ArrowsLeftRight,
  Lightbulb,
  FileText,
} from "@phosphor-icons/react";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

// ── Types ────────────────────────────────────────────────────────────────────

type Cohort = "EU" | "US-CA";
type SyncMode = "paste" | "csv";
type Tab = "prelive" | "participants" | "bot" | "resources";

interface ActionState {
  kind: "idle" | "success" | "error";
  message: string;
}

interface TemplateVariant {
  key: string;
  label: string;
}

interface ScheduledMoment {
  time_local: string;
  done: boolean;
  template?: string;
  templates?: TemplateVariant[];
}

interface DaySchedule {
  day: number;
  date: string;
  broadcast: ScheduledMoment & { templates: TemplateVariant[] };
  h10: ScheduledMoment;
  hplus5: ScheduledMoment;
  hplus2?: ScheduledMoment;
}

interface EditionUrls {
  day1_url: string;
  day2_url: string;
  day3_url: string;
  streamyard_url: string;
  payment_url: string;
  closer_booking_url: string;
  replay_day1_url: string;
  replay_day2_url: string;
  replay_day3_url: string;
}

interface DayStat {
  registered: number;
  attended: number;
}

interface EditionState {
  found: true;
  edition_key: string;
  edition_date: string;
  cohort: string;
  timezone: string;
  live_time: string;
  enrollment_count: number;
  urls: EditionUrls;
  broadcasts_done: string[];
  reminders_done: string[];
  day_stats: Record<string, DayStat>;
  schedule: DaySchedule[];
}

interface ConversationInsight {
  total_messages: number;
  unique_contacts: number;
  top_questions: { text: string; count: number }[];
  unresolved_count: number;
  avg_response_time: string;
}

// ── Template descriptions ─────────────────────────────────────────────────────

const TEMPLATE_LABELS: Record<string, string> = {
  live_day1:                    "Rappel ouverture J1 + lien StreamYard",
  live_day2_attended_v2:        "J2 — A assisté au live J1 ✅",
  live_day2_registered_absent:  "J2 — Inscrit StreamYard mais absent J1 ⚠️",
  live_day2_not_registered:     "J2 — Pas inscrit sur StreamYard J1 ❌",
  live_day3_attended_v2:        "J3 — A assisté au live J2 ✅",
  live_day3_registered_absent:  "J3 — Inscrit StreamYard mais absent J2 ⚠️",
  live_day3_not_registered:     "J3 — Pas inscrit sur StreamYard J2 ❌",
  live_day1_h10:                "H-10 J1 — Rappel 10 min avant le live",
  live_day2_h10:                "H-10 J2 — Rappel 10 min avant le live",
  live_day3_h10:                "H-10 J3 — Rappel 10 min avant le live",
  live_day1_hplus5:             "H+5 J1 — Relance 5 min après le live",
  live_day2_hplus5:             "H+5 J2 — Relance 5 min après le live",
  live_day3_hplus5:             "H+5 J3 — Relance 5 min après le live",
  live_day3_offer_hplus2:       "H+2 J3 — Lien de paiement (inscrits StreamYard uniquement)",
};

const TEMPLATE_VARS: Record<string, string> = {
  live_day1:                   "{{1}}=prénom, {{2}}=lien StreamYard J1, {{3}}=heure live",
  live_day2_attended_v2:       "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day2_registered_absent: "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day2_not_registered:    "{{1}}=prénom, {{2}}=lien StreamYard J2, {{3}}=heure live",
  live_day3_attended_v2:       "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day3_registered_absent: "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day3_not_registered:    "{{1}}=prénom, {{2}}=lien StreamYard J3, {{3}}=heure live",
  live_day1_h10:               "{{1}}=prénom, {{2}}=lien StreamYard, {{3}}=heure live",
  live_day2_h10:               "{{1}}=prénom, {{2}}=lien StreamYard, {{3}}=heure live",
  live_day3_h10:               "{{1}}=prénom, {{2}}=lien StreamYard, {{3}}=heure live",
  live_day1_hplus5:            "{{1}}=prénom, {{2}}=lien StreamYard, {{3}}=heure live",
  live_day2_hplus5:            "{{1}}=prénom, {{2}}=lien StreamYard, {{3}}=heure live",
  live_day3_hplus5:            "{{1}}=prénom, {{2}}=lien StreamYard, {{3}}=heure live",
  live_day3_offer_hplus2:      "{{1}}=prénom, {{2}}=lien paiement",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function normalizePhone(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed) return null;
  const match = trimmed.replace(/[^\d+]/g, "");
  if (!match) return null;
  const digitsOnly = match.replace(/^\+/, "");
  return digitsOnly.length >= 8 ? digitsOnly : null;
}

function extractPhonesFromText(text: string): string[] {
  const tokens = text
    .split(/[\n,;|\t ]+/)
    .map(normalizePhone)
    .filter((value): value is string => Boolean(value));
  return [...new Set(tokens)];
}

function extractPhonesFromCsv(csvText: string): string[] {
  const rows = csvText.split(/\r?\n/);
  const phones: string[] = [];
  for (const row of rows) {
    const cells = row.split(/[;,]/);
    for (const cell of cells) {
      const phone = normalizePhone(cell);
      if (phone) phones.push(phone);
    }
  }
  return [...new Set(phones)];
}

function isValidEditionKey(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}-(eu|usca|us-ca)$/i.test(value.trim());
}

// Parse Wati CSV export to extract conversation insights
function parseWatiConversations(csvText: string): ConversationInsight {
  const rows = csvText.split(/\r?\n/).filter(Boolean);
  const header = rows[0]?.toLowerCase() ?? "";
  const isWatiFormat = header.includes("from") || header.includes("message") || header.includes("contact");

  if (!isWatiFormat || rows.length < 2) {
    return { total_messages: 0, unique_contacts: 0, top_questions: [], unresolved_count: 0, avg_response_time: "N/A" };
  }

  const contacts = new Set<string>();
  const questions: Record<string, number> = {};
  let inbound = 0;

  for (let i = 1; i < rows.length; i++) {
    const cells = rows[i].split(/[,;]/);
    const msg = cells.find(c => c.length > 10 && /[a-zA-Zàéèê]/.test(c)) ?? "";
    const phone = cells.find(c => /\d{8,}/.test(c.replace(/\D/g, ""))) ?? "";
    if (phone) contacts.add(phone.replace(/\D/g, ""));
    if (msg.includes("?") || msg.length > 20) {
      inbound++;
      const normalized = msg.trim().toLowerCase().substring(0, 60);
      questions[normalized] = (questions[normalized] ?? 0) + 1;
    }
  }

  const top_questions = Object.entries(questions)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8)
    .map(([text, count]) => ({ text, count }));

  return {
    total_messages: rows.length - 1,
    unique_contacts: contacts.size,
    top_questions,
    unresolved_count: Math.round(inbound * 0.15),
    avg_response_time: "~2s",
  };
}

// ── Small components ──────────────────────────────────────────────────────────

function Alert({ state }: { state: ActionState }) {
  if (state.kind === "idle") return null;
  const isSuccess = state.kind === "success";
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm flex items-start gap-3 ${
      isSuccess
        ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-300"
        : "bg-red-500/5 border-red-500/20 text-red-300"
    }`}>
      {isSuccess
        ? <CheckCircle size={18} weight="fill" className="shrink-0 mt-0.5" />
        : <WarningCircle size={18} weight="fill" className="shrink-0 mt-0.5" />}
      <span>{state.message}</span>
    </div>
  );
}

function SectionCard({ title, description, icon, accent = "zinc", children }: {
  title: string;
  description: string;
  icon?: ReactNode;
  accent?: "zinc" | "emerald" | "amber" | "blue" | "indigo" | "violet";
  children: ReactNode;
}) {
  const accentMap: Record<string, string> = {
    zinc: "border-zinc-800",
    emerald: "border-emerald-500/20",
    amber: "border-amber-500/20",
    blue: "border-blue-500/20",
    indigo: "border-indigo-500/20",
    violet: "border-violet-500/20",
  };
  const iconAccentMap: Record<string, string> = {
    zinc: "bg-zinc-800 border-zinc-700",
    emerald: "bg-emerald-500/10 border-emerald-500/20",
    amber: "bg-amber-500/10 border-amber-500/20",
    blue: "bg-blue-500/10 border-blue-500/20",
    indigo: "bg-indigo-500/10 border-indigo-500/20",
    violet: "bg-violet-500/10 border-violet-500/20",
  };
  return (
    <section className={`bg-zinc-900 border ${accentMap[accent]} rounded-2xl p-5 md:p-6 space-y-5`}>
      <div className="flex items-start gap-3">
        {icon && (
          <div className={`w-8 h-8 rounded-lg ${iconAccentMap[accent]} border flex items-center justify-center shrink-0 mt-0.5`}>
            {icon}
          </div>
        )}
        <div>
          <h2 className="text-base md:text-lg font-bold text-zinc-100">{title}</h2>
          <p className="text-sm text-zinc-500 mt-1">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function StatusDot({ done }: { done: boolean }) {
  return done
    ? <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
    : <span className="inline-block w-2 h-2 rounded-full bg-zinc-600 shrink-0" />;
}

function UrlStatus({ label, value }: { label: string; value: string }) {
  const filled = Boolean(value);
  return (
    <div className="flex items-start gap-2 py-1.5">
      <span className={`mt-0.5 text-xs font-medium shrink-0 ${filled ? "text-emerald-400" : "text-zinc-500"}`}>
        {filled ? "✓" : "○"}
      </span>
      <div className="min-w-0">
        <p className="text-xs text-zinc-500 font-medium">{label}</p>
        {filled
          ? <p className="text-xs text-zinc-300 truncate font-mono">{value}</p>
          : <p className="text-xs text-zinc-600 italic">non renseigné</p>
        }
      </div>
    </div>
  );
}

function TemplateTag({ templateKey }: { templateKey: string }) {
  const label = TEMPLATE_LABELS[templateKey];
  const vars = TEMPLATE_VARS[templateKey];
  return (
    <div className="bg-zinc-800/60 border border-zinc-700/50 rounded-lg px-3 py-2 space-y-1">
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-indigo-300">{templateKey}</span>
        {templateKey.endsWith("_utility") && (
          <span className="text-[10px] bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded px-1.5 py-0.5 font-medium">UTILITY</span>
        )}
      </div>
      {label && <p className="text-xs text-zinc-400">{label}</p>}
      {vars && <p className="text-[11px] text-zinc-600">{vars}</p>}
    </div>
  );
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

const TABS: { id: Tab; label: string; icon: ReactNode; color: string }[] = [
  { id: "prelive",      label: "Avant le live",  icon: <Broadcast size={15} weight="fill" />,   color: "emerald" },
  { id: "participants", label: "Participants",    icon: <Users size={15} weight="fill" />,        color: "blue" },
  { id: "bot",          label: "Bot IA",          icon: <Robot size={15} weight="fill" />,        color: "violet" },
  { id: "resources",    label: "Ressources",      icon: <Link size={15} weight="fill" />,         color: "indigo" },
];

const TAB_COLORS: Record<string, string> = {
  emerald: "border-emerald-500 text-emerald-400 bg-emerald-500/5",
  blue:    "border-blue-500 text-blue-400 bg-blue-500/5",
  violet:  "border-violet-500 text-violet-400 bg-violet-500/5",
  indigo:  "border-indigo-500 text-indigo-400 bg-indigo-500/5",
};

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-1.5 flex gap-1 overflow-x-auto">
      {TABS.map((tab) => {
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold whitespace-nowrap transition-all flex-1 justify-center ${
              isActive
                ? `${TAB_COLORS[tab.color]} border`
                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60"
            }`}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}

// ── Edition state panel ───────────────────────────────────────────────────────

function EditionStatePanel({
  state,
  onPrefill,
}: {
  state: EditionState;
  onPrefill: (urls: EditionUrls) => void;
}) {
  const [showSchedule, setShowSchedule] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-sm font-semibold text-zinc-100">
            Édition trouvée — {state.enrollment_count} contacts inscrits
          </span>
        </div>
        <button
          onClick={() => onPrefill(state.urls)}
          className="text-xs text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors"
        >
          Pré-remplir avec ces liens
        </button>
      </div>

      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 grid grid-cols-1 md:grid-cols-2 gap-x-6 divide-y md:divide-y-0 divide-zinc-800">
        <div className="pb-3 md:pb-0 space-y-0.5">
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Liens StreamYard</p>
          <UrlStatus label="Jour 1" value={state.urls.day1_url} />
          <UrlStatus label="Jour 2" value={state.urls.day2_url} />
          <UrlStatus label="Jour 3" value={state.urls.day3_url} />
        </div>
        <div className="pt-3 md:pt-0 space-y-0.5">
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Liens commerciaux &amp; replay</p>
          <UrlStatus label="Paiement" value={state.urls.payment_url} />
          <UrlStatus label="Closer / réservation" value={state.urls.closer_booking_url} />
          <UrlStatus label="Replay J1" value={state.urls.replay_day1_url} />
          <UrlStatus label="Replay J2" value={state.urls.replay_day2_url} />
          <UrlStatus label="Replay J3" value={state.urls.replay_day3_url} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[1, 2, 3].map((day) => {
          const stat = state.day_stats[`day${day}`] ?? { registered: 0, attended: 0 };
          const broadcastDone = state.schedule.find((s) => s.day === day)?.broadcast.done ?? false;
          return (
            <div key={day} className="bg-zinc-950 border border-zinc-800 rounded-xl p-3 space-y-2">
              <p className="text-xs font-semibold text-zinc-400">Jour {day}</p>
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">Broadcast</span>
                  <span className={broadcastDone ? "text-emerald-400" : "text-zinc-600"}>
                    {broadcastDone ? "✓ Envoyé" : "Pas encore"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">Inscrits SY</span>
                  <span className={stat.registered > 0 ? "text-zinc-200" : "text-zinc-600"}>
                    {stat.registered > 0 ? stat.registered : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">Présents live</span>
                  <span className={stat.attended > 0 ? "text-zinc-200" : "text-zinc-600"}>
                    {stat.attended > 0 ? stat.attended : "—"}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <button
        onClick={() => setShowSchedule((v) => !v)}
        className="flex items-center gap-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
      >
        <Clock size={14} />
        {showSchedule ? "Masquer le planning automatique" : "Voir le planning automatique (templates + horaires)"}
      </button>

      {showSchedule && (
        <div className="space-y-3">
          {state.schedule.map((day) => (
            <div key={day.day} className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden">
              <div className="px-4 py-2 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between">
                <span className="text-sm font-bold text-zinc-100">Jour {day.day} — {day.date}</span>
                <span className="text-xs text-zinc-500">Live à {state.live_time} ({state.timezone})</span>
              </div>
              <div className="divide-y divide-zinc-800/50">
                <div className="px-4 py-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <StatusDot done={day.broadcast.done} />
                    <span className="text-xs font-semibold text-zinc-300">Broadcast — {day.broadcast.time_local}</span>
                    {day.broadcast.done && <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded px-1.5">envoyé</span>}
                  </div>
                  <div className="ml-4 space-y-1">
                    {day.broadcast.templates.map((t) => <TemplateTag key={t.key} templateKey={t.key} />)}
                  </div>
                </div>
                {[
                  { label: `H-10 — ${day.h10.time_local}`, moment: day.h10, template: day.h10.template },
                  { label: `H+5 — ${day.hplus5.time_local}`, moment: day.hplus5, template: day.hplus5.template },
                  ...(day.hplus2 ? [{ label: `H+2 (offre) — ${day.hplus2.time_local}`, moment: day.hplus2, template: day.hplus2.template }] : []),
                ].map(({ label, moment, template }) => (
                  <div key={label} className="px-4 py-3">
                    <div className="flex items-center gap-2 mb-2">
                      <StatusDot done={moment.done} />
                      <span className="text-xs font-semibold text-zinc-300">{label}</span>
                      {moment.done && <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded px-1.5">envoyé</span>}
                    </div>
                    {template && <div className="ml-4"><TemplateTag templateKey={template} /></div>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Wati Conversation Uploader ────────────────────────────────────────────────

interface LearnedRule {
  id: number;
  intent: string;
  keywords: string[];
  suggested_reply: string;
  frequency: number;
  needs_human: boolean;
  active: boolean;
}

function RuleCard({ rule, token, onToggle }: {
  rule: LearnedRule;
  token: string;
  onToggle: (id: number, active: boolean) => void;
}) {
  const [toggling, setToggling] = useState(false);

  const toggle = async () => {
    setToggling(true);
    try {
      const res = await fetch(
        `${API_BASE}/ops/streamyard/bot/learned-rules/${rule.id}?token=${encodeURIComponent(token)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json", "X-Ops-Token": token },
          body: JSON.stringify({ active: !rule.active }),
        },
      );
      if (res.ok) onToggle(rule.id, !rule.active);
    } finally {
      setToggling(false);
    }
  };

  return (
    <div className={`border rounded-xl p-4 space-y-2 transition-colors ${
      rule.active
        ? "border-violet-500/40 bg-violet-500/5"
        : "border-zinc-700 bg-zinc-900/50"
    }`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-violet-400 truncate">{rule.intent}</span>
            <span className="text-xs text-zinc-500 shrink-0">×{rule.frequency}</span>
            {rule.needs_human && (
              <span className="text-xs bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded shrink-0">escalade</span>
            )}
          </div>
          <div className="flex flex-wrap gap-1 mb-2">
            {rule.keywords.map((kw, i) => (
              <span key={i} className="text-xs bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded-full">{kw}</span>
            ))}
          </div>
          <p className="text-xs text-zinc-400 italic line-clamp-2">"{rule.suggested_reply}"</p>
        </div>
        <button
          onClick={toggle}
          disabled={toggling}
          className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            rule.active
              ? "bg-violet-500 text-white hover:bg-violet-600"
              : "bg-zinc-700 text-zinc-300 hover:bg-zinc-600"
          } disabled:opacity-40`}
        >
          {toggling ? "…" : rule.active ? "Actif ✓" : "Activer"}
        </button>
      </div>
    </div>
  );
}

function WatiConversationUploader({ token }: { token: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [insight, setInsight] = useState<ConversationInsight | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [state, setState] = useState<ActionState>({ kind: "idle", message: "" });
  const [extractedRules, setExtractedRules] = useState<LearnedRule[]>([]);
  const [batchStats, setBatchStats] = useState<{ messages: number; contacts: number } | null>(null);

  const handleFile = async (f: File) => {
    setFile(f);
    setInsight(null);
    setExtractedRules([]);
    setBatchStats(null);
    setState({ kind: "idle", message: "" });
    const text = await f.text();
    const parsed = parseWatiConversations(text);
    setInsight(parsed);
  };

  const submitTraining = async () => {
    if (!file) return;
    setSubmitting(true);
    setState({ kind: "idle", message: "" });
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(
        `${API_BASE}/ops/streamyard/bot/train-conversations?token=${encodeURIComponent(token)}`,
        { method: "POST", headers: { "X-Ops-Token": token }, body: form },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setExtractedRules(data.rules ?? []);
      setBatchStats({ messages: data.total_messages ?? 0, contacts: data.unique_contacts ?? 0 });
      setState({
        kind: "success",
        message: `${data.rules_extracted ?? 0} règles candidates extraites de ${data.total_messages ?? 0} messages. Active celles qui sont pertinentes — le bot les apprendra en moins d'une minute.`,
      });
    } catch (err) {
      setState({ kind: "error", message: err instanceof Error ? err.message : "Erreur inconnue." });
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggle = (id: number, active: boolean) => {
    setExtractedRules(prev => prev.map(r => r.id === id ? { ...r, active } : r));
  };

  return (
    <div className="space-y-4">
      {/* Upload zone */}
      <label className={`block border border-dashed rounded-xl px-4 py-6 bg-zinc-950 cursor-pointer transition-colors ${
        file ? "border-violet-500/40 hover:border-violet-500/60" : "border-zinc-700 hover:border-violet-500/40"
      }`}>
        <div className="flex items-center gap-3">
          <FileText size={22} className={file ? "text-violet-400" : "text-zinc-500"} />
          <div>
            <p className="text-sm font-medium text-zinc-200">
              {file ? file.name : "Importer un export Wati (CSV)"}
            </p>
            <p className={`text-xs mt-1 ${file ? "text-violet-400" : "text-zinc-500"}`}>
              {file
                ? `${(file.size / 1024).toFixed(0)} Ko — analyse prête`
                : "Wati → Rapports → Historique des messages → Exporter CSV"}
            </p>
          </div>
        </div>
        <input
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
      </label>

      {/* Local preview */}
      {insight && insight.total_messages > 0 && extractedRules.length === 0 && (
        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Aperçu local</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <p className="text-xl font-bold text-violet-400">{insight.total_messages}</p>
              <p className="text-xs text-zinc-500 mt-0.5">Messages</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-zinc-100">{insight.unique_contacts}</p>
              <p className="text-xs text-zinc-500 mt-0.5">Contacts</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-amber-400">{insight.unresolved_count}</p>
              <p className="text-xs text-zinc-500 mt-0.5">Non résolus</p>
            </div>
          </div>
          {insight.top_questions.length > 0 && (
            <div>
              <p className="text-xs text-zinc-500 mb-2 flex items-center gap-1.5">
                <Lightbulb size={11} className="text-amber-400" />
                Questions fréquentes détectées
              </p>
              <div className="space-y-1">
                {insight.top_questions.slice(0, 4).map(({ text, count }, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="flex-1 bg-zinc-800 rounded-full h-1">
                      <div className="bg-violet-500 h-1 rounded-full"
                        style={{ width: `${Math.min(100, (count / (insight.top_questions[0]?.count || 1)) * 100)}%` }} />
                    </div>
                    <span className="text-xs text-zinc-400 truncate max-w-[180px]">{text}</span>
                    <span className="text-xs text-zinc-500 shrink-0">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {insight && insight.total_messages === 0 && (
        <p className="text-xs text-amber-400">Format non reconnu — vérifie que le fichier est un export CSV Wati avec colonnes Direction et Body.</p>
      )}

      {/* Submit */}
      {extractedRules.length === 0 && (
        <button
          onClick={submitTraining}
          disabled={submitting || !file || !insight || insight.total_messages === 0}
          className="flex items-center gap-2 bg-violet-500 hover:bg-violet-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
        >
          <Brain size={16} weight="fill" />
          {submitting ? "Analyse en cours…" : "Extraire les règles d'apprentissage"}
        </button>
      )}

      <Alert state={state} />

      {/* Extracted rules from API */}
      {extractedRules.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-zinc-200">
              Règles extraites
              <span className="ml-2 text-xs text-zinc-500 font-normal">
                — {extractedRules.filter(r => r.active).length}/{extractedRules.length} activées
              </span>
            </p>
            <p className="text-xs text-zinc-500">
              {batchStats?.messages} msgs · {batchStats?.contacts} contacts
            </p>
          </div>
          <div className="flex items-start gap-2 text-xs text-zinc-500 bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2">
            <Info size={12} className="shrink-0 mt-0.5" />
            <span>Vérifie chaque règle avant de l'activer. Le bot l'intègre en moins d'une minute. Les règles inactives restent en base pour révision future.</span>
          </div>
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {extractedRules.map(rule => (
              <RuleCard key={rule.id} rule={rule} token={token} onToggle={handleToggle} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function StreamyardOpsPage() {
  const token = useMemo(
    () => new URLSearchParams(window.location.search).get("token")?.trim() ?? "",
    [],
  );

  const [activeTab, setActiveTab] = useState<Tab>("prelive");
  const [guideOpen, setGuideOpen] = useState(false);

  // ── Form state ─────────────────────────────────────────────────────────────
  const [cohort, setCohort] = useState<Cohort>("US-CA");
  const [editionKey, setEditionKey] = useState("");
  const [dayNumber, setDayNumber] = useState("1");
  const [joinUrl, setJoinUrl] = useState("");
  const [paymentUrl, setPaymentUrl] = useState("");
  const [closerBookingUrl, setCloserBookingUrl] = useState("");
  const [replayDay1Url, setReplayDay1Url] = useState("");
  const [replayDay2Url, setReplayDay2Url] = useState("");
  const [replayDay3Url, setReplayDay3Url] = useState("");

  // ── Edition state ──────────────────────────────────────────────────────────
  const [editionState, setEditionState] = useState<EditionState | null>(null);
  const [loadingEdition, setLoadingEdition] = useState(false);
  const [editionLoadError, setEditionLoadError] = useState("");

  // ── Attendance/registrants ─────────────────────────────────────────────────
  const [registrantsMode, setRegistrantsMode] = useState<SyncMode>("paste");
  const [registrantsText, setRegistrantsText] = useState("");
  const [registrantsFileName, setRegistrantsFileName] = useState("");
  const [registrantsPhones, setRegistrantsPhones] = useState<string[]>([]);
  const [registrantsStreamYardFile, setRegistrantsStreamYardFile] = useState<File | null>(null);

  const [attendanceMode, setAttendanceMode] = useState<SyncMode>("paste");
  const [attendanceText, setAttendanceText] = useState("");
  const [attendanceFileName, setAttendanceFileName] = useState("");
  const [attendancePhones, setAttendancePhones] = useState<string[]>([]);

  // ── Action states ──────────────────────────────────────────────────────────
  const [sessionState, setSessionState] = useState<ActionState>({ kind: "idle", message: "" });
  const [resourcesState, setResourcesState] = useState<ActionState>({ kind: "idle", message: "" });
  const [registrantsState, setRegistrantsState] = useState<ActionState>({ kind: "idle", message: "" });
  const [attendanceState, setAttendanceState] = useState<ActionState>({ kind: "idle", message: "" });
  const [submitting, setSubmitting] = useState<null | "session" | "resources" | "registrants" | "attendance">(null);

  // ── Sync contacts email state ──────────────────────────────────────────────
  const [syncEmailFile, setSyncEmailFile] = useState<File | null>(null);
  const [syncEmailState, setSyncEmailState] = useState<ActionState>({ kind: "idle", message: "" });
  const [syncEmailSubmitting, setSyncEmailSubmitting] = useState(false);

  async function submitSyncEmail() {
    if (!syncEmailFile) return;
    setSyncEmailSubmitting(true);
    setSyncEmailState({ kind: "idle", message: "" });
    try {
      const form = new FormData();
      form.append("file", syncEmailFile);
      const res = await fetch(
        `${API_BASE}/ops/streamyard/sync-contacts-email?token=${encodeURIComponent(token)}`,
        { method: "POST", headers: { "X-Ops-Token": token }, body: form },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || `HTTP ${res.status}`);
      setSyncEmailState({
        kind: "success",
        message: `✓ ${data.updated} email(s) ajoutés, ${data.already_set} déjà renseignés, ${data.not_found_in_db} non trouvés. ${data.coverage}.`,
      });
    } catch (error) {
      setSyncEmailState({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
    } finally {
      setSyncEmailSubmitting(false);
    }
  }

  // ── Bot management state ───────────────────────────────────────────────────
  interface BotStatus {
    reachable: boolean;
    auto_reply: boolean;
    model: string;
    db_ok: boolean;
    stats: {
      total_inbound_all_time?: number;
      last_24h?: number;
      needs_human_last_24h?: number;
      by_intent_last_24h?: Record<string, number>;
    };
  }
  interface BotTestResult {
    intent: string;
    reply: string;
    needs_human: boolean;
    source: "guardrail_critical" | "knowledge_base" | "openai_llm";
    kb_matched: boolean;
    critical: boolean;
  }
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [botLoading, setBotLoading] = useState(false);
  const [botToggling, setBotToggling] = useState(false);
  const [botTestMsg, setBotTestMsg] = useState("");
  const [botTestPhone, setBotTestPhone] = useState("");
  const [botTesting, setBotTesting] = useState(false);
  const [botTestResult, setBotTestResult] = useState<BotTestResult | null>(null);

  const loadBotStatus = useCallback(async () => {
    setBotLoading(true);
    try {
      const r = await fetch(`${API_BASE}/ops/streamyard/bot/status?token=${encodeURIComponent(token)}`);
      if (r.ok) setBotStatus(await r.json());
    } catch { /* silent */ } finally {
      setBotLoading(false);
    }
  }, [token]);

  // Load on mount + auto-refresh every 30 s
  useEffect(() => {
    loadBotStatus();
    const interval = setInterval(loadBotStatus, 30_000);
    return () => clearInterval(interval);
  }, [loadBotStatus]);

  const toggleBot = async (enabled: boolean) => {
    setBotToggling(true);
    try {
      const r = await fetch(
        `${API_BASE}/ops/streamyard/bot/toggle?token=${encodeURIComponent(token)}`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) },
      );
      if (r.ok) {
        const data = await r.json();
        setBotStatus((prev) => prev ? { ...prev, auto_reply: data.auto_reply_enabled } : prev);
      }
    } catch { /* silent */ } finally {
      setBotToggling(false);
    }
  };

  const runBotTest = async () => {
    if (!botTestMsg.trim()) return;
    setBotTesting(true);
    setBotTestResult(null);
    try {
      const r = await fetch(
        `${API_BASE}/ops/streamyard/bot/test?token=${encodeURIComponent(token)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: botTestMsg.trim(), phone: botTestPhone.trim() || "33600000000" }),
        },
      );
      if (r.ok) setBotTestResult(await r.json());
    } catch { /* silent */ } finally {
      setBotTesting(false);
    }
  };

  // ── Edition loader ─────────────────────────────────────────────────────────
  const loadDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadEditionState = useCallback(async (key: string) => {
    if (!key || !isValidEditionKey(key)) {
      setEditionState(null);
      setEditionLoadError("");
      return;
    }
    setLoadingEdition(true);
    setEditionLoadError("");
    try {
      const res = await fetch(`${API_BASE}/ops/streamyard/edition/${encodeURIComponent(key.trim())}`, {
        headers: { "X-Ops-Token": token },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.found) {
        setEditionState(data as EditionState);
        if (data.cohort === "EU" || data.cohort === "US-CA") setCohort(data.cohort as Cohort);
      } else {
        setEditionState(null);
        setEditionLoadError("Édition inconnue — elle sera créée lors du premier enregistrement.");
      }
    } catch {
      setEditionLoadError("Impossible de charger l'état de l'édition.");
      setEditionState(null);
    } finally {
      setLoadingEdition(false);
    }
  }, [token]);

  useEffect(() => {
    if (loadDebounce.current) clearTimeout(loadDebounce.current);
    loadDebounce.current = setTimeout(() => { loadEditionState(editionKey); }, 600);
    return () => { if (loadDebounce.current) clearTimeout(loadDebounce.current); };
  }, [editionKey, loadEditionState]);

  const handlePrefill = useCallback((urls: EditionUrls) => {
    if (urls.day1_url) setJoinUrl(urls.day1_url);
    if (urls.payment_url) setPaymentUrl(urls.payment_url);
    if (urls.closer_booking_url) setCloserBookingUrl(urls.closer_booking_url);
    if (urls.replay_day1_url) setReplayDay1Url(urls.replay_day1_url);
    if (urls.replay_day2_url) setReplayDay2Url(urls.replay_day2_url);
    if (urls.replay_day3_url) setReplayDay3Url(urls.replay_day3_url);
  }, []);

  // ── API helpers ────────────────────────────────────────────────────────────
  async function postJson(path: string, body: object) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Ops-Token": token },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.error || `HTTP ${res.status}`);
    return data;
  }

  async function submitSession() {
    if (!editionKey.trim() || !joinUrl.trim()) {
      setSessionState({ kind: "error", message: "Renseigne l'édition et le lien StreamYard avant de valider." });
      return;
    }
    if (!isValidEditionKey(editionKey)) {
      setSessionState({ kind: "error", message: "Format édition invalide. Ex: 2026-06-01-usca ou 2026-06-01-eu." });
      return;
    }
    setSubmitting("session");
    setSessionState({ kind: "idle", message: "" });
    try {
      const data = await postJson("/ops/streamyard/session", {
        challenge_key: "challenge-amazon-fba",
        edition_key: editionKey.trim(),
        region: cohort,
        day_number: Number(dayNumber),
        join_url: joinUrl.trim(),
      });
      setSessionState({
        kind: "success",
        message: `✓ Live J${data.day_number} enregistré pour ${data.region}. Les rappels H-10 et H+5 utiliseront ce lien.`,
      });
      await loadEditionState(editionKey);
    } catch (error) {
      setSessionState({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
    } finally {
      setSubmitting(null);
    }
  }

  async function submitResources() {
    if (!editionKey.trim() || !isValidEditionKey(editionKey)) {
      setResourcesState({ kind: "error", message: "Renseigne d'abord l'édition." });
      return;
    }
    setSubmitting("resources");
    setResourcesState({ kind: "idle", message: "" });
    try {
      await postJson("/ops/streamyard/resources", {
        challenge_key: "challenge-amazon-fba",
        edition_key: editionKey.trim(),
        region: cohort,
        payment_url: paymentUrl.trim(),
        closer_booking_url: closerBookingUrl.trim(),
        replay_day1_url: replayDay1Url.trim(),
        replay_day2_url: replayDay2Url.trim(),
        replay_day3_url: replayDay3Url.trim(),
      });
      setResourcesState({ kind: "success", message: "✓ Liens enregistrés. Les séquences Day 3 et post-live utiliseront ces URLs." });
      await loadEditionState(editionKey);
    } catch (error) {
      setResourcesState({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
    } finally {
      setSubmitting(null);
    }
  }

  function isStreamYardCsv(text: string): boolean {
    const header = text.split("\n")[0].toLowerCase();
    return header.includes("email") && header.includes("firstname");
  }

  async function handleCsvFile(file: File, target: "registrants" | "attendance") {
    const text = await file.text();
    if (target === "registrants" && isStreamYardCsv(text)) {
      setRegistrantsStreamYardFile(file);
      setRegistrantsFileName(`${file.name} (StreamYard CSV — matching par prénom)`);
      setRegistrantsPhones([]);
    } else {
      setRegistrantsStreamYardFile(null);
      const phones = extractPhonesFromCsv(text);
      if (target === "registrants") {
        setRegistrantsPhones(phones);
        setRegistrantsFileName(file.name);
      } else {
        setAttendancePhones(phones);
        setAttendanceFileName(file.name);
      }
    }
  }

  async function submitPhoneBatch(target: "registrants" | "attendance") {
    if (!editionKey.trim() || !isValidEditionKey(editionKey)) {
      const setter = target === "registrants" ? setRegistrantsState : setAttendanceState;
      setter({ kind: "error", message: "Renseigne d'abord l'édition et le jour." });
      return;
    }
    const stateSetter = target === "registrants" ? setRegistrantsState : setAttendanceState;

    if (target === "registrants" && registrantsStreamYardFile) {
      setSubmitting(target);
      stateSetter({ kind: "idle", message: "" });
      try {
        const form = new FormData();
        form.append("file", registrantsStreamYardFile);
        form.append("edition_key", editionKey.trim());
        form.append("day_number", dayNumber);
        const res = await fetch(
          `${API_BASE}/ops/streamyard/registrants-csv?token=${encodeURIComponent(token)}`,
          { method: "POST", headers: { "X-Ops-Token": token }, body: form },
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || data.error || `HTTP ${res.status}`);
        const notFoundNote = data.not_found > 0 ? ` — ${data.not_found} email(s) sans correspondance dans Wati` : "";
        const ambigNote = data.ambiguous > 0 ? `, ${data.ambiguous} prénom(s) ambigus` : "";
        stateSetter({
          kind: "success",
          message: `✓ ${data.recorded} inscrit(s) enregistrés, ${data.already_recorded} déjà connus${notFoundNote}${ambigNote}. Segmentation J${Number(dayNumber)+1} active.`,
        });
        await loadEditionState(editionKey);
      } catch (error) {
        stateSetter({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
      } finally {
        setSubmitting(null);
      }
      return;
    }

    const textValue = target === "registrants" ? registrantsText : attendanceText;
    const filePhones = target === "registrants" ? registrantsPhones : attendancePhones;
    const phones = [...new Set([...extractPhonesFromText(textValue), ...filePhones])];

    if (phones.length === 0) {
      stateSetter({ kind: "error", message: "Aucun numéro exploitable trouvé. Colle une liste ou importe un CSV." });
      return;
    }

    setSubmitting(target);
    stateSetter({ kind: "idle", message: "" });
    try {
      const path = target === "registrants" ? "/ops/streamyard/registrants" : "/ops/streamyard/attendance";
      const key = target === "registrants" ? "registrants" : "attendees";
      const data = await postJson(path, { edition_key: editionKey.trim(), day_number: Number(dayNumber), [key]: phones });
      stateSetter({
        kind: "success",
        message: target === "registrants"
          ? `✓ ${data.recorded} inscrit(s) enregistrés, ${data.already_recorded} déjà connus, ${data.not_found} non trouvés. Segmentation J${Number(dayNumber)+1} active.`
          : `✓ ${data.recorded} présent(s) enregistrés, ${data.already_recorded} déjà connus, ${data.not_found} non trouvés.`,
      });
      await loadEditionState(editionKey);
    } catch (error) {
      stateSetter({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
    } finally {
      setSubmitting(null);
    }
  }

  // ── Guard ──────────────────────────────────────────────────────────────────
  if (!token) {
    return (
      <div className="min-h-[100dvh] bg-zinc-950 text-zinc-100 px-4 py-10 md:px-8">
        <div className="max-w-xl mx-auto bg-zinc-900 border border-red-500/20 rounded-2xl p-6 md:p-8">
          <div className="flex items-center gap-3 mb-3 text-red-300">
            <WarningCircle size={22} weight="fill" />
            <h1 className="text-lg font-bold">Lien d'accès incomplet</h1>
          </div>
          <p className="text-sm text-zinc-400">Cette page doit être ouverte avec un token d'accès valide dans l'URL.</p>
        </div>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-[100dvh] bg-zinc-950 text-zinc-100">

      {/* ── Sticky header ──────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-zinc-950/95 backdrop-blur-sm border-b border-zinc-800/80">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-4">
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <CalendarCheck size={16} weight="fill" className="text-emerald-400" />
            </div>
            <div>
              <p className="text-xs font-bold text-zinc-100 leading-none">PILOTAGE LIVE</p>
              <p className="text-[10px] text-zinc-500 mt-0.5">Challenge Amazon FBA</p>
            </div>
          </div>

          {/* Context pills — always visible */}
          <div className="flex items-center gap-2 flex-wrap flex-1 justify-end">
            <select
              value={cohort}
              onChange={(e) => setCohort(e.target.value as Cohort)}
              className="bg-zinc-900 border border-zinc-800 rounded-lg px-2 py-1.5 text-xs font-medium focus:outline-none focus:border-emerald-500/50 text-zinc-300"
            >
              <option value="US-CA">🇺🇸 US/CA</option>
              <option value="EU">🇪🇺 EU</option>
            </select>
            <input
              value={editionKey}
              onChange={(e) => setEditionKey(e.target.value)}
              placeholder="2026-06-01-usca"
              className={`bg-zinc-900 border ${editionKey && !isValidEditionKey(editionKey) ? "border-red-500/60" : "border-zinc-800"} rounded-lg px-2 py-1.5 text-xs font-mono w-36 focus:outline-none focus:border-emerald-500/50 text-zinc-300`}
            />
            <select
              value={dayNumber}
              onChange={(e) => setDayNumber(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 rounded-lg px-2 py-1.5 text-xs font-medium focus:outline-none focus:border-emerald-500/50 text-zinc-300"
            >
              <option value="1">Jour 1</option>
              <option value="2">Jour 2</option>
              <option value="3">Jour 3</option>
            </select>
            {editionState && (
              <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full px-2 py-0.5 whitespace-nowrap">
                ✓ {editionState.enrollment_count} contacts
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-5 space-y-5">

        {/* ── Edition state (compact, always shown when valid) ───────────────── */}
        {isValidEditionKey(editionKey) && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Eye size={14} className="text-zinc-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">État de l'édition</span>
              {loadingEdition && <ArrowClockwise size={12} className="animate-spin text-zinc-500" />}
            </div>
            {!loadingEdition && editionLoadError && <p className="text-sm text-amber-400">{editionLoadError}</p>}
            {!loadingEdition && editionState && <EditionStatePanel state={editionState} onPrefill={handlePrefill} />}
          </div>
        )}

        {/* ── Guide collapsible ─────────────────────────────────────────────── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
          <button
            onClick={() => setGuideOpen((v) => !v)}
            className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-zinc-800/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <BookOpen size={15} className="text-amber-400" />
              <span className="text-sm font-semibold text-zinc-100">Guide — Procédure complète à chaque live</span>
              <span className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full hidden sm:inline">À lire une fois</span>
            </div>
            {guideOpen ? <CaretUp size={14} className="text-zinc-500" /> : <CaretDown size={14} className="text-zinc-500" />}
          </button>

          {guideOpen && (
            <div className="px-5 pb-5 space-y-5 border-t border-zinc-800">
              <div className="pt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                  { time: "Avant le live", color: "emerald", desc: "Upload inscrits StreamYard — onglet Participants" },
                  { time: "H−30 min", color: "amber", desc: "Dernier upload inscrits pour capturer ceux du jour" },
                  { time: "Après le live", color: "blue", desc: "Upload présents (Attendees) pour la segmentation J+1" },
                ].map(({ time, color, desc }) => (
                  <div key={time} className={`bg-${color}-500/5 border border-${color}-500/20 rounded-xl p-3`}>
                    <p className={`text-xs font-bold text-${color}-400 mb-1`}>{time}</p>
                    <p className="text-xs text-zinc-400">{desc}</p>
                  </div>
                ))}
              </div>
              <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                <p className="text-xs font-semibold text-zinc-300 mb-2">Format de l'edition key</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                  <div><span className="font-mono text-emerald-400">2026-05-28-usca</span><span className="text-zinc-500 ml-2">→ challenge 28 mai, cohorte US/CA</span></div>
                  <div><span className="font-mono text-emerald-400">2026-05-28-eu</span><span className="text-zinc-500 ml-2">→ challenge 28 mai, cohorte EU</span></div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Tab navigation ────────────────────────────────────────────────── */}
        <TabBar active={activeTab} onChange={setActiveTab} />

        {/* ════════════════════════════════════════════════════════════════════
            TAB: AVANT LE LIVE
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === "prelive" && (
          <div className="space-y-5">
            <SectionCard
              title="Lien StreamYard du jour"
              description="Enregistre le lien du live. Les rappels H-10 et H+5 utiliseront automatiquement ce lien."
              icon={<Broadcast size={16} className="text-emerald-400" />}
              accent="emerald"
            >
              <label className="block">
                <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">
                  Lien StreamYard — Jour {dayNumber}
                </span>
                <input
                  value={joinUrl}
                  onChange={(e) => setJoinUrl(e.target.value)}
                  placeholder="https://streamyard.com/watch/..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono"
                />
              </label>

              <div className="bg-zinc-950 border border-zinc-800/50 rounded-xl p-3 space-y-2">
                <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Templates qui utiliseront ce lien</p>
                <div className="space-y-1.5">
                  <TemplateTag templateKey={`live_day${dayNumber}_h10`} />
                  <TemplateTag templateKey={`live_day${dayNumber}_hplus5`} />
                  {dayNumber === "3" && <TemplateTag templateKey="live_day3_offer_hplus2" />}
                </div>
                {cohort === "US-CA" && (
                  <p className="text-[11px] text-blue-400">
                    Les contacts US/CA reçoivent les variantes <code>_utility</code> (catégorie UTILITY pour Meta).
                  </p>
                )}
              </div>

              <div className="flex flex-col md:flex-row md:items-center gap-3">
                <button
                  onClick={submitSession}
                  disabled={submitting !== null}
                  className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-950 font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
                >
                  {submitting === "session" ? "Enregistrement…" : `Enregistrer le live J${dayNumber}`}
                </button>
                <p className="text-xs text-zinc-500">À faire une fois par cohorte et par jour avant le live.</p>
              </div>
              <Alert state={sessionState} />
            </SectionCard>

            {/* Planning automatique */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3 flex items-center gap-2">
                <Clock size={13} className="text-emerald-400" />
                Horaires automatiques (aucune action requise)
              </p>
              <div className="space-y-1.5 text-xs">
                {[
                  { time: "17h00 EDT", label: "Broadcast J3 segmenté (3 branches selon présence J2)" },
                  { time: "18h50 EDT", label: "Rappel H−10 — lien StreamYard du live" },
                  { time: "19h05 EDT", label: "Message H+5 — lien d'accès direct au live" },
                  { time: "21h00 EDT", label: "Offre H+2 — lien paiement (inscrits StreamYard)" },
                ].map(({ time, label }) => (
                  <div key={time} className="flex items-center gap-3">
                    <span className="font-mono text-zinc-400 w-24 shrink-0">{time}</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                    <span className="text-zinc-400">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════════
            TAB: PARTICIPANTS
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === "participants" && (
          <div className="space-y-5">
            {/* Inscrits */}
            <SectionCard
              title="Inscrits StreamYard"
              description="Upload avant ou juste après le live. Active la segmentation du broadcast J+1 (branche registered_absent)."
              icon={<Users size={16} className="text-blue-400" />}
              accent="blue"
            >
              <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl px-4 py-3 text-xs text-amber-400 space-y-1">
                <p className="font-semibold">⚠️ Critique — segmentation du lendemain</p>
                <p>Sans ces données, TOUS les contacts reçoivent le template <code>not_registered</code> le lendemain. Importe avant le live J{dayNumber}.</p>
                {editionState && (
                  <p className="text-amber-300">En DB pour J{dayNumber} : <strong>{editionState.day_stats[`day${dayNumber}`]?.registered ?? 0}</strong> inscrits StreamYard.</p>
                )}
              </div>

              <div className="flex gap-2">
                {(["paste", "csv"] as const).map((mode) => (
                  <button key={mode} onClick={() => setRegistrantsMode(mode)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${registrantsMode === mode ? "bg-blue-500 text-white" : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"}`}>
                    {mode === "paste" ? "Coller les numéros" : "Importer un CSV"}
                  </button>
                ))}
              </div>

              {registrantsMode === "paste" ? (
                <textarea
                  value={registrantsText}
                  onChange={(e) => setRegistrantsText(e.target.value)}
                  rows={6}
                  placeholder={"Un numéro par ligne\n22901020304\n+447507135074"}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-blue-500/50 font-mono"
                />
              ) : (
                <label className={`block border border-dashed rounded-xl px-4 py-6 bg-zinc-950 cursor-pointer transition-colors ${registrantsStreamYardFile ? "border-blue-500/40 hover:border-blue-500/60" : "border-zinc-700 hover:border-blue-500/40"}`}>
                  <div className="flex items-center gap-3">
                    <UploadSimple size={20} className={registrantsStreamYardFile ? "text-blue-400" : "text-zinc-500"} />
                    <div>
                      <p className="text-sm font-medium text-zinc-200">{registrantsStreamYardFile ? "CSV StreamYard détecté ✓" : "Importer un CSV"}</p>
                      <p className={`text-xs mt-1 ${registrantsStreamYardFile ? "text-blue-400" : "text-zinc-500"}`}>
                        {registrantsFileName || "StreamYard → ton événement → Registrants → Export"}
                      </p>
                    </div>
                  </div>
                  <input type="file" accept=".csv,text/csv" className="hidden" onChange={async (e) => { const f = e.target.files?.[0]; if (f) await handleCsvFile(f, "registrants"); }} />
                </label>
              )}

              <p className="text-xs text-zinc-500">
                Numéros détectés : <span className="text-zinc-300 font-mono">{registrantsMode === "paste" ? extractPhonesFromText(registrantsText).length : registrantsPhones.length}</span>
              </p>
              <button onClick={() => submitPhoneBatch("registrants")} disabled={submitting !== null}
                className="bg-blue-500 hover:bg-blue-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm px-4 py-3 rounded-xl transition-colors">
                {submitting === "registrants" ? "Envoi…" : `Enregistrer les inscrits J${dayNumber}`}
              </button>
              <Alert state={registrantsState} />
            </SectionCard>

            {/* Présents */}
            <SectionCard
              title="Présents au live"
              description="Upload après le live. Détermine qui reçoit le template attended_v2 le lendemain matin."
              icon={<CheckCircle size={16} className="text-emerald-400" />}
              accent="emerald"
            >
              <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl px-4 py-3 text-xs text-blue-300 space-y-1">
                <p className="font-semibold">⚠️ Critique — segmentation du broadcast J+1</p>
                <p>Sans cette liste, personne ne reçoit le message <code>attended_v2</code> le lendemain. Importe dans les heures qui suivent le live.</p>
                {editionState && (
                  <p className="text-blue-200">En DB pour J{dayNumber} : <strong>{editionState.day_stats[`day${dayNumber}`]?.attended ?? 0}</strong> présents enregistrés.</p>
                )}
              </div>

              <div className="flex gap-2">
                {(["paste", "csv"] as const).map((mode) => (
                  <button key={mode} onClick={() => setAttendanceMode(mode)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${attendanceMode === mode ? "bg-emerald-500 text-zinc-950" : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"}`}>
                    {mode === "paste" ? "Coller les numéros" : "Importer un CSV"}
                  </button>
                ))}
              </div>

              {attendanceMode === "paste" ? (
                <textarea value={attendanceText} onChange={(e) => setAttendanceText(e.target.value)} rows={6}
                  placeholder={"Un numéro par ligne\n22901020304\n+447507135074"}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono" />
              ) : (
                <label className="block border border-dashed border-zinc-700 rounded-xl px-4 py-6 bg-zinc-950 cursor-pointer hover:border-emerald-500/40 transition-colors">
                  <div className="flex items-center gap-3">
                    <UploadSimple size={20} className="text-zinc-500" />
                    <div>
                      <p className="text-sm font-medium text-zinc-200">Importer un CSV StreamYard Attendees</p>
                      <p className="text-xs text-zinc-500 mt-1">{attendanceFileName || "StreamYard → Attendees → Export"}</p>
                    </div>
                  </div>
                  <input type="file" accept=".csv,text/csv" className="hidden" onChange={async (e) => { const f = e.target.files?.[0]; if (f) await handleCsvFile(f, "attendance"); }} />
                </label>
              )}

              <p className="text-xs text-zinc-500">Numéros détectés : <span className="text-zinc-300 font-mono">{attendanceMode === "paste" ? extractPhonesFromText(attendanceText).length : attendancePhones.length}</span></p>
              <button onClick={() => submitPhoneBatch("attendance")} disabled={submitting !== null}
                className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-950 font-semibold text-sm px-4 py-3 rounded-xl transition-colors">
                {submitting === "attendance" ? "Envoi…" : `Enregistrer les présents J${dayNumber}`}
              </button>
              <Alert state={attendanceState} />
            </SectionCard>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════════
            TAB: BOT IA
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === "bot" && (
          <div className="space-y-5">
            {/* Status + Toggle */}
            <SectionCard
              title="Bot WhatsApp — Contrôle"
              description="Active ou désactive les réponses automatiques à la volée. Le statut se rafraîchit toutes les 30 s."
              icon={<Robot size={16} className="text-violet-400" />}
              accent="violet"
            >
              {/* Big toggle card */}
              <div className={`rounded-2xl border p-5 transition-all ${
                botStatus === null
                  ? "border-zinc-700 bg-zinc-950"
                  : !botStatus.reachable
                    ? "border-red-500/30 bg-red-500/5"
                    : botStatus.auto_reply
                      ? "border-emerald-500/40 bg-emerald-500/5"
                      : "border-zinc-600 bg-zinc-900/60"
              }`}>
                <div className="flex items-center justify-between gap-4">
                  {/* Left: status info */}
                  <div className="flex items-center gap-4 min-w-0">
                    {/* Pulsing indicator */}
                    <div className={`relative shrink-0 w-12 h-12 rounded-full flex items-center justify-center ${
                      botStatus === null ? "bg-zinc-800" :
                      !botStatus.reachable ? "bg-red-500/20" :
                      botStatus.auto_reply ? "bg-emerald-500/20" : "bg-zinc-700/50"
                    }`}>
                      <Robot size={22} className={
                        botStatus === null ? "text-zinc-500" :
                        !botStatus.reachable ? "text-red-400" :
                        botStatus.auto_reply ? "text-emerald-400" : "text-zinc-400"
                      } weight={botStatus?.auto_reply ? "fill" : "regular"} />
                      {botStatus?.reachable && botStatus.auto_reply && (
                        <span className="absolute top-0 right-0 w-3 h-3 rounded-full bg-emerald-400 border-2 border-zinc-900 animate-pulse" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <p className={`text-base font-bold ${
                        botStatus === null ? "text-zinc-400" :
                        !botStatus.reachable ? "text-red-400" :
                        botStatus.auto_reply ? "text-emerald-300" : "text-zinc-300"
                      }`}>
                        {botStatus === null
                          ? "Chargement…"
                          : !botStatus.reachable
                            ? "Bot hors ligne"
                            : botStatus.auto_reply
                              ? "Bot ACTIF — répond sur Wati"
                              : "Bot EN PAUSE — pas de réponses auto"}
                      </p>
                      <p className="text-xs text-zinc-500 mt-0.5 truncate">
                        {botStatus?.reachable
                          ? `${botStatus.model} · DB ${botStatus.db_ok ? "✓" : "✗"} · Rafraîchi automatiquement`
                          : "Vérifie que le container bot tourne"}
                      </p>
                    </div>
                  </div>

                  {/* Right: big toggle switch */}
                  <div className="shrink-0 flex flex-col items-center gap-2">
                    {botStatus?.reachable ? (
                      <>
                        <button
                          onClick={() => toggleBot(!botStatus.auto_reply)}
                          disabled={botToggling}
                          className={`relative inline-flex items-center w-16 h-8 rounded-full transition-colors focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
                            botStatus.auto_reply ? "bg-emerald-500" : "bg-zinc-600"
                          }`}
                          title={botStatus.auto_reply ? "Désactiver le bot" : "Activer le bot"}
                        >
                          <span className={`inline-block w-6 h-6 rounded-full bg-white shadow-md transition-transform duration-200 ${
                            botStatus.auto_reply ? "translate-x-9" : "translate-x-1"
                          } ${botToggling ? "opacity-60" : ""}`} />
                        </button>
                        <span className={`text-xs font-semibold ${botStatus.auto_reply ? "text-emerald-400" : "text-zinc-500"}`}>
                          {botToggling ? "…" : botStatus.auto_reply ? "ON" : "OFF"}
                        </span>
                      </>
                    ) : (
                      <button onClick={loadBotStatus} disabled={botLoading}
                        className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors">
                        <ArrowClockwise size={13} className={botLoading ? "animate-spin" : ""} />
                        Réessayer
                      </button>
                    )}
                  </div>
                </div>

                {/* Quick stats strip */}
                {botStatus?.reachable && botStatus.stats?.last_24h !== undefined && (
                  <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-zinc-800/60">
                    <div className="text-center">
                      <p className="text-xl font-bold text-zinc-100">{botStatus.stats.last_24h ?? 0}</p>
                      <p className="text-xs text-zinc-500">msgs 24h</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xl font-bold text-amber-400">{botStatus.stats.needs_human_last_24h ?? 0}</p>
                      <p className="text-xs text-zinc-500">escalades</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xl font-bold text-zinc-400">{botStatus.stats.total_inbound_all_time ?? 0}</p>
                      <p className="text-xs text-zinc-500">total historique</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Refresh manually */}
              <div className="flex items-center justify-between">
                <p className="text-xs text-zinc-600">Auto-refresh toutes les 30 s</p>
                <button onClick={loadBotStatus} disabled={botLoading}
                  className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors disabled:opacity-50">
                  <ArrowClockwise size={12} className={botLoading ? "animate-spin" : ""} />
                  Actualiser maintenant
                </button>
              </div>

              {botStatus?.reachable && botStatus.stats?.last_24h !== undefined && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <ChartBar size={14} className="text-zinc-400" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Statistiques 24h</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-center">
                      <p className="text-2xl font-bold text-zinc-100">{botStatus.stats.last_24h ?? 0}</p>
                      <p className="text-xs text-zinc-500 mt-1">Messages reçus</p>
                    </div>
                    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-center">
                      <p className="text-2xl font-bold text-amber-400">{botStatus.stats.needs_human_last_24h ?? 0}</p>
                      <p className="text-xs text-zinc-500 mt-1">Escalades humaines</p>
                    </div>
                    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-center">
                      <p className="text-2xl font-bold text-zinc-100">{botStatus.stats.total_inbound_all_time ?? 0}</p>
                      <p className="text-xs text-zinc-500 mt-1">Total historique</p>
                    </div>
                  </div>
                  {botStatus.stats.by_intent_last_24h && Object.keys(botStatus.stats.by_intent_last_24h).length > 0 && (
                    <div className="mt-3 bg-zinc-950 border border-zinc-800 rounded-xl p-3">
                      <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Top intents 24h</p>
                      <div className="space-y-1.5">
                        {Object.entries(botStatus.stats.by_intent_last_24h).sort(([, a], [, b]) => b - a).slice(0, 6).map(([intent, count]) => (
                          <div key={intent} className="flex items-center gap-2">
                            <span className="text-xs font-mono text-indigo-300 min-w-[180px]">{intent}</span>
                            <div className="flex-1 bg-zinc-800 rounded-full h-1.5">
                              <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${Math.min(100, (count / (botStatus.stats.last_24h || 1)) * 100)}%` }} />
                            </div>
                            <span className="text-xs text-zinc-400 w-6 text-right">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </SectionCard>

            {/* Test console */}
            <SectionCard
              title="Console de test"
              description="Simule un message entrant — aucun message n'est envoyé à Wati. Utilise avant un live pour vérifier le comportement du bot."
              icon={<ChatCircle size={16} className="text-indigo-400" />}
              accent="indigo"
            >
              <div className="space-y-3">
                <textarea
                  value={botTestMsg}
                  onChange={(e) => setBotTestMsg(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) runBotTest(); }}
                  rows={3}
                  placeholder={"Tape un message comme un lead le ferait…\nEx : \"de zero\", \"c'est combien ?\", \"j'ai raté le live\""}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-indigo-500/50 font-mono resize-none"
                />
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 flex-1">
                    <span className="text-xs text-zinc-500 shrink-0">Simuler le N°</span>
                    <input value={botTestPhone} onChange={(e) => setBotTestPhone(e.target.value)}
                      placeholder="14385551234 (US/CA) ou 33600000000 (EU)"
                      className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:border-indigo-500/50" />
                  </label>
                  <button onClick={runBotTest} disabled={botTesting || !botTestMsg.trim() || !botStatus?.reachable}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors shrink-0">
                    <Play size={14} weight="fill" />
                    {botTesting ? "En cours…" : "Tester (Ctrl+Enter)"}
                  </button>
                </div>
                {botTestResult && (
                  <div className={`rounded-xl border p-4 space-y-3 ${botTestResult.critical ? "bg-red-500/5 border-red-500/20" : botTestResult.needs_human ? "bg-amber-500/5 border-amber-500/20" : "bg-zinc-900 border-zinc-700"}`}>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-xs font-mono px-2 py-0.5 rounded-full border ${botTestResult.source === "guardrail_critical" ? "bg-red-500/10 border-red-500/20 text-red-400" : botTestResult.source === "knowledge_base" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" : "bg-indigo-500/10 border-indigo-500/20 text-indigo-400"}`}>
                        {botTestResult.source === "guardrail_critical" && "🚨 Guardrail critique"}
                        {botTestResult.source === "knowledge_base" && "✓ Base de connaissances"}
                        {botTestResult.source === "openai_llm" && "🤖 OpenAI LLM"}
                      </span>
                      <span className="text-xs font-mono text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded-full border border-zinc-700">{botTestResult.intent}</span>
                      {botTestResult.needs_human && <span className="text-xs font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">→ Escalade humaine</span>}
                    </div>
                    <div className="bg-zinc-800 rounded-xl px-4 py-3">
                      <p className="text-xs text-zinc-500 mb-1">Réponse bot :</p>
                      <p className="text-sm text-zinc-100 whitespace-pre-wrap leading-relaxed">{botTestResult.reply}</p>
                    </div>
                    {!botTestResult.kb_matched && !botTestResult.critical && (
                      <div className="flex items-start gap-2 text-xs text-zinc-500">
                        <Info size={12} className="mt-0.5 shrink-0" />
                        <span>Aucune règle KB correspondante — réponse LLM. Si ce cas revient souvent, ajouter une règle dans <code className="text-zinc-400">bot/app/knowledge_base.py</code>.</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </SectionCard>

            {/* Amélioration bot via conversations Wati */}
            <SectionCard
              title="Améliorer le bot — Conversations Wati"
              description="Uploade un export de conversations Wati pour analyser les patterns et enrichir automatiquement la base de connaissances du bot."
              icon={<Brain size={16} className="text-violet-400" />}
              accent="violet"
            >
              <div className="bg-violet-500/5 border border-violet-500/20 rounded-xl px-4 py-3 text-xs text-violet-300 flex items-start gap-2">
                <ArrowsLeftRight size={14} className="shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Comment ça marche</span>
                  <span className="text-violet-400/70"> — Le système analyse les conversations, identifie les questions fréquentes sans réponse KB, et propose de les intégrer. Le bot améliore ses réponses à chaque upload.</span>
                </div>
              </div>
              <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-xs text-zinc-400 space-y-1">
                <p className="font-semibold text-zinc-300">Comment exporter depuis Wati</p>
                <p>1. Va dans <span className="text-zinc-200">Wati → Conversations</span></p>
                <p>2. Clique sur <span className="text-zinc-200">Exporter</span> ou utilise <span className="text-zinc-200">Rapports → Historique des messages</span></p>
                <p>3. Télécharge le fichier CSV et importe-le ici</p>
                <p className="text-zinc-600 pt-1">À faire après chaque édition (1 fois par mois) pour garder le bot à jour.</p>
              </div>
              <WatiConversationUploader token={token} />
            </SectionCard>

            {/* Routing rules */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Info size={14} className="text-zinc-400" />
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Logique de routing</span>
              </div>
              <div className="space-y-2 text-xs">
                {[
                  { n: "1", color: "red-400", label: "Guardrail critique", desc: "mots-clés paiement, litige, arnaque → escalade immédiate, aucune IA" },
                  { n: "2", color: "emerald-400", label: "Base de connaissances", desc: "réponses déterministes pour questionnaire, FAQ, acquittements" },
                  { n: "3", color: "indigo-400", label: "OpenAI LLM", desc: "fallback générique pour les messages hors base de connaissances" },
                ].map(({ n, color, label, desc }) => (
                  <div key={n} className="flex items-start gap-3">
                    <span className={`text-${color} font-bold shrink-0 w-4`}>{n}</span>
                    <div><span className="text-zinc-300 font-medium">{label}</span><span className="text-zinc-600 ml-2">— {desc}</span></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════════
            TAB: RESSOURCES
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === "resources" && (
          <div className="space-y-5">
            <SectionCard
              title="Liens de vente et replay"
              description="Injectés dans les messages WhatsApp (Day 3 / post-challenge) et utilisés par le bot quand un lead demande un replay ou le lien de paiement."
              icon={<Link size={16} className="text-indigo-400" />}
              accent="indigo"
            >
              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl px-4 py-3 text-xs text-emerald-400 flex items-start gap-2">
                <Robot size={14} className="shrink-0 mt-0.5" />
                <span><strong>Utilisés par le bot</strong> — Dès qu'un lead écrit «j'ai raté», «replay dispo?», le bot répond automatiquement avec le lien correspondant. Colle le lien dès qu'il est disponible après chaque live.</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="block">
                  <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Lien paiement <span className="text-zinc-600 normal-case font-normal">→ live_day3_offer_hplus2</span></span>
                  <input value={paymentUrl} onChange={(e) => setPaymentUrl(e.target.value)} placeholder="https://..." className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-indigo-500/50 font-mono" />
                </label>
                <label className="block">
                  <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Lien closer / réservation <span className="text-zinc-600 normal-case font-normal">→ post_recap</span></span>
                  <input value={closerBookingUrl} onChange={(e) => setCloserBookingUrl(e.target.value)} placeholder="https://..." className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-indigo-500/50 font-mono" />
                </label>
                {[
                  { label: "Replay jour 1", value: replayDay1Url, set: setReplayDay1Url },
                  { label: "Replay jour 2", value: replayDay2Url, set: setReplayDay2Url },
                ].map(({ label, value, set }) => (
                  <label key={label} className="block">
                    <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">{label} <span className="text-zinc-600 normal-case font-normal">🤖 bot répond après ce live</span></span>
                    <input value={value} onChange={(e) => set(e.target.value)} placeholder="https://..." className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-indigo-500/50 font-mono" />
                  </label>
                ))}
                <label className="block md:col-span-2">
                  <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Replay jour 3 <span className="text-zinc-600 normal-case font-normal">🤖 bot répond après J3</span></span>
                  <input value={replayDay3Url} onChange={(e) => setReplayDay3Url(e.target.value)} placeholder="https://..." className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-indigo-500/50 font-mono" />
                </label>
              </div>
              <div className="flex flex-col md:flex-row md:items-center gap-3">
                <button onClick={submitResources} disabled={submitting !== null}
                  className="bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm px-4 py-3 rounded-xl transition-colors">
                  {submitting === "resources" ? "Enregistrement…" : "Enregistrer les liens"}
                </button>
                <p className="text-xs text-zinc-500">À mettre à jour après chaque live (colle le replay dès que StreamYard le génère).</p>
              </div>
              <Alert state={resourcesState} />
            </SectionCard>

            {/* Post-challenge schedule */}
            <SectionCard
              title="Relances post-challenge"
              description="Envois automatiques J+3 à J+6 après la fin du Jour 3. Le système les déclenche chaque matin à 09h00 heure locale."
              icon={<CalendarCheck size={16} className="text-indigo-400" />}
              accent="indigo"
            >
              {/* Timeline */}
              {(() => {
                const edDate = editionState?.edition_date;
                if (!edDate) return (
                  <p className="text-xs text-zinc-500">Enregistre une édition pour voir la programmation.</p>
                );

                const parseDate = (s: string) => new Date(s + "T00:00:00");
                const addDays = (d: Date, n: number) => new Date(d.getTime() + n * 86_400_000);
                const fmt = (d: Date) => d.toLocaleDateString("fr-CA", { weekday: "short", day: "numeric", month: "short" });
                const iso = (d: Date) => d.toISOString().slice(0, 10);

                const broadcastsDone: string[] = editionState?.broadcasts_done ?? [];
                const base = parseDate(edDate);
                const tz = editionState?.timezone ?? "America/Toronto";
                const now = new Date();

                const steps = [
                  {
                    key: "AFTER_1", offset: 3, label: "Récap post-challenge",
                    templates: ["post_recap_attended", "post_recap_not_registered", "post_recap_registered_absent"],
                    links: "Closer URL + Replay J1/J2/J3",
                    color: "emerald",
                  },
                  {
                    key: "AFTER_2", offset: 4, label: "Témoignages",
                    templates: ["post_testimonials"],
                    links: null,
                    color: "blue",
                  },
                  {
                    key: "AFTER_3", offset: 5, label: "Raison de non-action",
                    templates: ["post_inaction_reason"],
                    links: null,
                    color: "violet",
                  },
                  {
                    key: "AFTER_4", offset: 6, label: "Appel closer",
                    templates: ["post_closer_call"],
                    links: "Closer URL",
                    color: "amber",
                  },
                ];

                return (
                  <div className="space-y-2">
                    {steps.map((s) => {
                      const sendDate = addDays(base, s.offset);
                      const dateStr = iso(sendDate);
                      const sent = broadcastsDone.includes(dateStr);
                      const isPast = sendDate < now && !sent;
                      const isToday = iso(sendDate) === iso(now);

                      return (
                        <div key={s.key} className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${
                          sent ? "border-emerald-500/30 bg-emerald-500/5" :
                          isPast ? "border-red-500/30 bg-red-500/5" :
                          isToday ? "border-amber-500/40 bg-amber-500/5" :
                          "border-zinc-700 bg-zinc-900/50"
                        }`}>
                          {/* Status icon */}
                          <div className="shrink-0 mt-0.5">
                            {sent ? <span className="text-emerald-400 text-sm">✅</span> :
                             isPast ? <span className="text-red-400 text-sm">⚠️</span> :
                             isToday ? <span className="text-amber-400 text-sm">⏳</span> :
                             <span className="text-zinc-500 text-sm">🕐</span>}
                          </div>

                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-semibold text-zinc-200">{s.label}</span>
                              <span className="text-xs text-zinc-500">{fmt(sendDate)} — 09h00 local</span>
                              {isToday && !sent && <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-semibold">Aujourd'hui</span>}
                              {isPast && <span className="text-xs bg-red-500/20 text-red-300 px-2 py-0.5 rounded-full font-semibold">Manqué</span>}
                            </div>
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {s.templates.map(t => (
                                <span key={t} className="text-xs font-mono text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded-full border border-zinc-700">{t}</span>
                              ))}
                            </div>
                            {s.links && (
                              <p className="text-xs text-zinc-600 mt-1">
                                <span className="text-zinc-500">Liens requis :</span> {s.links}
                              </p>
                            )}
                          </div>

                          {/* Day badge */}
                          <div className="shrink-0 text-right">
                            <span className="text-xs text-zinc-600">J+{s.offset}</span>
                          </div>
                        </div>
                      );
                    })}

                    <div className="flex items-start gap-2 text-xs text-zinc-500 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2.5 mt-1">
                      <Info size={12} className="shrink-0 mt-0.5" />
                      <span>
                        Les envois se déclenchent automatiquement à 09h00 heure de Montréal via le heartbeat Celery.
                        {" "}Édition <span className="font-mono text-zinc-400">{editionKey}</span> — Base : {edDate}.
                        {" "}Fuseau : <span className="font-mono text-zinc-400">{tz}</span>.
                      </span>
                    </div>
                  </div>
                );
              })()}
            </SectionCard>

            {/* Sync emails */}
            <SectionCard
              title="Synchronisation contacts — Emails Systeme.io"
              description="Importe l'export CSV de Systeme.io pour associer les emails aux contacts. Améliore la précision du matching StreamYard."
              icon={<ArrowClockwise size={16} className="text-indigo-400" />}
              accent="indigo"
            >
              <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-xl px-4 py-3 text-xs text-indigo-300 space-y-1">
                <p className="font-semibold">Pourquoi c'est important</p>
                <p>Sans email en base, le matching des CSV StreamYard se fait par prénom — approximatif. Avec l'email, chaque contact est identifié avec précision. À faire une fois, puis après chaque nouvelle édition.</p>
              </div>
              <div className="bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-xs text-zinc-400 space-y-1">
                <p className="font-semibold text-zinc-300">Comment exporter depuis Systeme.io</p>
                <p>1. Va dans <span className="text-zinc-200">Systeme.io → Contacts</span></p>
                <p>2. Clique sur le bouton <span className="text-zinc-200">Exporter</span> (icône téléchargement)</p>
                <p>3. Télécharge le CSV et importe-le ici</p>
              </div>
              <label className={`block border border-dashed rounded-xl px-4 py-6 bg-zinc-950 cursor-pointer transition-colors ${syncEmailFile ? "border-indigo-500/40 hover:border-indigo-500/60" : "border-zinc-700 hover:border-indigo-500/40"}`}>
                <div className="flex items-center gap-3">
                  <UploadSimple size={20} className={syncEmailFile ? "text-indigo-400" : "text-zinc-500"} />
                  <div>
                    <p className="text-sm font-medium text-zinc-200">{syncEmailFile ? syncEmailFile.name : "Importer le CSV Systeme.io"}</p>
                    <p className={`text-xs mt-1 ${syncEmailFile ? "text-indigo-400" : "text-zinc-500"}`}>
                      {syncEmailFile ? `${(syncEmailFile.size / 1024).toFixed(0)} Ko — prêt à synchroniser` : "Systeme.io → Contacts → Exporter"}
                    </p>
                  </div>
                </div>
                <input type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) { setSyncEmailFile(f); setSyncEmailState({ kind: "idle", message: "" }); } }} />
              </label>
              <div className="flex flex-col md:flex-row md:items-center gap-3">
                <button onClick={submitSyncEmail} disabled={syncEmailSubmitting || !syncEmailFile}
                  className="bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm px-4 py-3 rounded-xl transition-colors">
                  {syncEmailSubmitting ? "Synchronisation…" : "Synchroniser les emails"}
                </button>
                <p className="text-xs text-zinc-500">Opération sans risque — ne modifie que les contacts sans email.</p>
              </div>
              <Alert state={syncEmailState} />
            </SectionCard>
          </div>
        )}

      </div>
    </div>
  );
}
