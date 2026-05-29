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
} from "@phosphor-icons/react";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

// ── Types ────────────────────────────────────────────────────────────────────

type Cohort = "EU" | "US-CA";
type SyncMode = "paste" | "csv";

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

// ── Template descriptions (human-readable labels) ─────────────────────────────

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

function SectionCard({ title, description, icon, children }: {
  title: string;
  description: string;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 md:p-6 space-y-5">
      <div className="flex items-start gap-3">
        {icon && (
          <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center shrink-0 mt-0.5">
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
      {/* Header */}
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
          Pré-remplir le formulaire avec ces liens
        </button>
      </div>

      {/* URL status grid */}
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

      {/* Per-day attendance stats */}
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

      {/* Schedule toggle */}
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
                {/* Broadcast */}
                <div className="px-4 py-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <StatusDot done={day.broadcast.done} />
                    <span className="text-xs font-semibold text-zinc-300">
                      Broadcast — {day.broadcast.time_local}
                    </span>
                    {day.broadcast.done && (
                      <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded px-1.5">envoyé</span>
                    )}
                  </div>
                  <div className="ml-4 space-y-1">
                    {day.broadcast.templates.map((t) => (
                      <TemplateTag key={t.key} templateKey={t.key} />
                    ))}
                    {day.day > 1 && (
                      <p className="text-[11px] text-amber-500/80 flex items-start gap-1 mt-1">
                        <WarningCircle size={12} className="shrink-0 mt-0.5" />
                        La variante envoyée dépend des inscrits/présents du jour précédent.
                        Importe ces données via les sections 2 et 3 ci-dessous.
                      </p>
                    )}
                  </div>
                </div>

                {/* H-10 */}
                <div className="px-4 py-3">
                  <div className="flex items-center gap-2 mb-2">
                    <StatusDot done={day.h10.done} />
                    <span className="text-xs font-semibold text-zinc-300">
                      H-10 — {day.h10.time_local}
                    </span>
                    {day.h10.done && (
                      <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded px-1.5">envoyé</span>
                    )}
                  </div>
                  <div className="ml-4">
                    <TemplateTag templateKey={day.h10.template!} />
                  </div>
                </div>

                {/* H+5 */}
                <div className="px-4 py-3">
                  <div className="flex items-center gap-2 mb-2">
                    <StatusDot done={day.hplus5.done} />
                    <span className="text-xs font-semibold text-zinc-300">
                      H+5 — {day.hplus5.time_local}
                    </span>
                    {day.hplus5.done && (
                      <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded px-1.5">envoyé</span>
                    )}
                  </div>
                  <div className="ml-4">
                    <TemplateTag templateKey={day.hplus5.template!} />
                  </div>
                </div>

                {/* H+2 (Day 3 only) */}
                {day.hplus2 && (
                  <div className="px-4 py-3">
                    <div className="flex items-center gap-2 mb-2">
                      <StatusDot done={day.hplus2.done} />
                      <span className="text-xs font-semibold text-zinc-300">
                        H+2 (offre) — {day.hplus2.time_local}
                      </span>
                      {day.hplus2.done && (
                        <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded px-1.5">envoyé</span>
                      )}
                    </div>
                    <div className="ml-4">
                      <TemplateTag templateKey={day.hplus2.template!} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
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

  // ── Edition state (loaded from API) ───────────────────────────────────────
  const [editionState, setEditionState] = useState<EditionState | null>(null);
  const [loadingEdition, setLoadingEdition] = useState(false);
  const [editionLoadError, setEditionLoadError] = useState("");

  // ── Attendance/registrants ─────────────────────────────────────────────────
  const [registrantsMode, setRegistrantsMode] = useState<SyncMode>("paste");
  const [registrantsText, setRegistrantsText] = useState("");
  const [registrantsFileName, setRegistrantsFileName] = useState("");
  const [registrantsPhones, setRegistrantsPhones] = useState<string[]>([]);

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

  // ── Debounced edition loader ───────────────────────────────────────────────
  const loadDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadEditionState = useCallback(
    async (key: string) => {
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
          // Auto-sync cohort from loaded edition
          if (data.cohort === "EU" || data.cohort === "US-CA") {
            setCohort(data.cohort as Cohort);
          }
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
    },
    [token],
  );

  useEffect(() => {
    if (loadDebounce.current) clearTimeout(loadDebounce.current);
    loadDebounce.current = setTimeout(() => {
      loadEditionState(editionKey);
    }, 600);
    return () => {
      if (loadDebounce.current) clearTimeout(loadDebounce.current);
    };
  }, [editionKey, loadEditionState]);

  // ── Pre-fill form from loaded edition ─────────────────────────────────────
  const handlePrefill = useCallback((urls: EditionUrls) => {
    if (urls.day1_url) setJoinUrl(urls.day1_url); // sensible default for day 1
    if (urls.payment_url) setPaymentUrl(urls.payment_url);
    if (urls.closer_booking_url) setCloserBookingUrl(urls.closer_booking_url);
    if (urls.replay_day1_url) setReplayDay1Url(urls.replay_day1_url);
    if (urls.replay_day2_url) setReplayDay2Url(urls.replay_day2_url);
    if (urls.replay_day3_url) setReplayDay3Url(urls.replay_day3_url);
  }, []);

  // ── API helpers ────────────────────────────────────────────────────────────
  const commonPayload = () => ({
    edition_key: editionKey.trim(),
    day_number: Number(dayNumber),
  });

  async function postJson(path: string, body: object) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Ops-Token": token,
      },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.error || `HTTP ${res.status}`);
    }
    return data;
  }

  // ── Submit handlers ────────────────────────────────────────────────────────
  async function submitSession() {
    if (!editionKey.trim() || !joinUrl.trim()) {
      setSessionState({ kind: "error", message: "Renseigne l'édition et le lien StreamYard avant de valider." });
      return;
    }
    if (!isValidEditionKey(editionKey)) {
      setSessionState({ kind: "error", message: "Format édition invalide. Utilise par exemple 2026-06-01-usca ou 2026-06-01-eu." });
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
      // Reload edition state after save
      await loadEditionState(editionKey);
    } catch (error) {
      setSessionState({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
    } finally {
      setSubmitting(null);
    }
  }

  async function submitResources() {
    if (!editionKey.trim()) {
      setResourcesState({ kind: "error", message: "Renseigne d'abord l'édition." });
      return;
    }
    if (!isValidEditionKey(editionKey)) {
      setResourcesState({ kind: "error", message: "Format édition invalide." });
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
      setResourcesState({
        kind: "success",
        message: "✓ Liens enregistrés. Les séquences Day 3 et post-live utiliseront ces URLs.",
      });
      await loadEditionState(editionKey);
    } catch (error) {
      setResourcesState({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
    } finally {
      setSubmitting(null);
    }
  }

  async function handleCsvFile(file: File, target: "registrants" | "attendance") {
    const text = await file.text();
    const phones = extractPhonesFromCsv(text);
    if (target === "registrants") {
      setRegistrantsPhones(phones);
      setRegistrantsFileName(file.name);
    } else {
      setAttendancePhones(phones);
      setAttendanceFileName(file.name);
    }
  }

  async function submitPhoneBatch(target: "registrants" | "attendance") {
    if (!editionKey.trim() || !isValidEditionKey(editionKey)) {
      const setter = target === "registrants" ? setRegistrantsState : setAttendanceState;
      setter({ kind: "error", message: "Renseigne d'abord l'édition et le jour." });
      return;
    }

    const stateSetter = target === "registrants" ? setRegistrantsState : setAttendanceState;
    const textValue = target === "registrants" ? registrantsText : attendanceText;
    const filePhones = target === "registrants" ? registrantsPhones : attendancePhones;
    const pastedPhones = extractPhonesFromText(textValue);
    const phones = [...new Set([...pastedPhones, ...filePhones])];

    if (phones.length === 0) {
      stateSetter({ kind: "error", message: "Aucun numéro exploitable trouvé. Colle une liste ou importe un CSV." });
      return;
    }

    setSubmitting(target);
    stateSetter({ kind: "idle", message: "" });
    try {
      const path = target === "registrants" ? "/ops/streamyard/registrants" : "/ops/streamyard/attendance";
      const key = target === "registrants" ? "registrants" : "attendees";
      const data = await postJson(path, {
        ...commonPayload(),
        [key]: phones,
      });
      stateSetter({
        kind: "success",
        message:
          target === "registrants"
            ? `✓ ${data.recorded} inscrit(s) enregistrés, ${data.already_recorded} déjà connus, ${data.not_found} non trouvés dans la DB. La segmentation J${Number(dayNumber)+1} est maintenant active.`
            : `✓ ${data.recorded} présent(s) enregistrés, ${data.already_recorded} déjà connus, ${data.not_found} non trouvés. La segmentation du broadcast J${Number(dayNumber)+1} est maintenant active.`,
      });
      await loadEditionState(editionKey);
    } catch (error) {
      stateSetter({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
    } finally {
      setSubmitting(null);
    }
  }

  // ── Guard: no token ────────────────────────────────────────────────────────
  if (!token) {
    return (
      <div className="min-h-[100dvh] bg-zinc-950 text-zinc-100 px-4 py-10 md:px-8">
        <div className="max-w-xl mx-auto bg-zinc-900 border border-red-500/20 rounded-2xl p-6 md:p-8">
          <div className="flex items-center gap-3 mb-3 text-red-300">
            <WarningCircle size={22} weight="fill" />
            <h1 className="text-lg font-bold">Lien d'accès incomplet</h1>
          </div>
          <p className="text-sm text-zinc-400">
            Cette page doit être ouverte avec un token d'accès valide dans l'URL.
          </p>
        </div>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-[100dvh] bg-zinc-950 text-zinc-100 px-4 py-6 md:px-8 md:py-8">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 md:p-6">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
              <CalendarCheck size={20} weight="fill" className="text-emerald-400" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-500 font-semibold">Opérations StreamYard</p>
              <h1 className="text-xl md:text-2xl font-bold text-zinc-100 mt-1">PILOTAGE LIVE</h1>
              <p className="text-sm text-zinc-400 mt-2">
                Remplis les infos du live. La plateforme se charge du reste — broadcast, H-10, H+5, H+2 se déclenchent automatiquement.
              </p>
            </div>
          </div>
        </div>

        {/* ── Contexte du live ─────────────────────────────────────────────── */}
        <SectionCard
          title="Contexte du live"
          description="Ces champs s'appliquent à toutes les actions ci-dessous. Renseigne-les une fois, puis enchaîne."
          icon={<ListChecks size={16} className="text-zinc-400" />}
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <label className="block">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Cohorte</span>
              <select
                value={cohort}
                onChange={(e) => setCohort(e.target.value as Cohort)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50"
              >
                <option value="US-CA">US/CA (19h00 Montréal)</option>
                <option value="EU">EU (21h00 Paris)</option>
              </select>
            </label>
            <label className="block md:col-span-2">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Edition key</span>
              <input
                value={editionKey}
                onChange={(e) => setEditionKey(e.target.value)}
                placeholder="2026-05-22-usca"
                className={`w-full bg-zinc-950 border ${
                  editionKey && !isValidEditionKey(editionKey)
                    ? "border-red-500/60"
                    : "border-zinc-800"
                } rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50`}
              />
              <span className="block text-[11px] text-zinc-600 mt-1">
                Format : AAAA-MM-JJ-eu ou AAAA-MM-JJ-usca
              </span>
            </label>
            <label className="block">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Jour</span>
              <select
                value={dayNumber}
                onChange={(e) => setDayNumber(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50"
              >
                <option value="1">Jour 1</option>
                <option value="2">Jour 2</option>
                <option value="3">Jour 3</option>
              </select>
            </label>
          </div>
        </SectionCard>

        {/* ── État de l'édition ────────────────────────────────────────────── */}
        {isValidEditionKey(editionKey) && (
          <SectionCard
            title="État de l'édition"
            description="Données actuellement enregistrées en base — vérifie avant chaque live."
            icon={<Eye size={16} className="text-zinc-400" />}
          >
            {loadingEdition && (
              <div className="flex items-center gap-2 text-sm text-zinc-400">
                <ArrowClockwise size={16} className="animate-spin" />
                Chargement…
              </div>
            )}
            {!loadingEdition && editionLoadError && (
              <p className="text-sm text-amber-400">{editionLoadError}</p>
            )}
            {!loadingEdition && editionState && (
              <EditionStatePanel state={editionState} onPrefill={handlePrefill} />
            )}
            {!loadingEdition && !editionState && !editionLoadError && (
              <p className="text-sm text-zinc-500">Saisis une édition valide pour voir son état.</p>
            )}
          </SectionCard>
        )}

        {/* ── 1. Avant le live — lien StreamYard ──────────────────────────── */}
        <SectionCard
          title="1. Avant le live — lien StreamYard"
          description="Enregistre le lien du jour. Les rappels H-10 et H+5 utiliseront automatiquement ce lien."
          icon={<Link size={16} className="text-zinc-400" />}
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

          {/* Preview templates */}
          <div className="bg-zinc-950 border border-zinc-800/50 rounded-xl p-3 space-y-2">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Templates qui utiliseront ce lien</p>
            <div className="space-y-1.5">
              <TemplateTag templateKey={`live_day${dayNumber}_h10`} />
              <TemplateTag templateKey={`live_day${dayNumber}_hplus5`} />
              {dayNumber === "3" && <TemplateTag templateKey="live_day3_offer_hplus2" />}
            </div>
            {cohort === "US-CA" && (
              <p className="text-[11px] text-blue-400">
                Les contacts US/CA reçoivent les variantes <code>_utility</code> (même contenu, catégorie UTILITY pour Meta).
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

        {/* ── 1 bis. Liens commerciaux et replay ──────────────────────────── */}
        <SectionCard
          title="1 bis. Liens de vente et replay"
          description="Renseigne une seule fois par édition. Ces liens s'injectent automatiquement dans les messages Day 3 et post-challenge."
          icon={<Link size={16} className="text-zinc-400" />}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">
                Lien paiement
                <span className="ml-2 text-zinc-600 normal-case font-normal">→ live_day3_offer_hplus2 ({{2}})</span>
              </span>
              <input
                value={paymentUrl}
                onChange={(e) => setPaymentUrl(e.target.value)}
                placeholder="https://..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono"
              />
            </label>
            <label className="block">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">
                Lien closer / réservation
                <span className="ml-2 text-zinc-600 normal-case font-normal">→ post_recap / post_closer_call ({{2}})</span>
              </span>
              <input
                value={closerBookingUrl}
                onChange={(e) => setCloserBookingUrl(e.target.value)}
                placeholder="https://..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono"
              />
            </label>
            <label className="block">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Replay jour 1</span>
              <input value={replayDay1Url} onChange={(e) => setReplayDay1Url(e.target.value)} placeholder="https://..." className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono" />
            </label>
            <label className="block">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Replay jour 2</span>
              <input value={replayDay2Url} onChange={(e) => setReplayDay2Url(e.target.value)} placeholder="https://..." className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono" />
            </label>
            <label className="block md:col-span-2">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Replay jour 3</span>
              <input value={replayDay3Url} onChange={(e) => setReplayDay3Url(e.target.value)} placeholder="https://..." className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono" />
            </label>
          </div>
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            <button
              onClick={submitResources}
              disabled={submitting !== null}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-950 font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
            >
              {submitting === "resources" ? "Enregistrement…" : "Enregistrer les liens"}
            </button>
            <p className="text-xs text-zinc-500">À faire une fois par édition, puis à mettre à jour si les URLs changent.</p>
          </div>
          <Alert state={resourcesState} />
        </SectionCard>

        {/* ── 2. Inscrits StreamYard ───────────────────────────────────────── */}
        <SectionCard
          title="2. Juste avant / au début du live — Inscrits StreamYard"
          description="Envoie la liste des numéros inscrits sur la page StreamYard. Cela active la segmentation J+1 (branche registered_absent)."
          icon={<Users size={16} className="text-zinc-400" />}
        >
          {/* Segmentation warning */}
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl px-4 py-3 text-xs text-amber-400 space-y-1">
            <p className="font-semibold">Pourquoi c'est critique</p>
            <p>Sans ces données, TOUS les contacts reçoivent le template <code>not_registered</code> le lendemain — même ceux qui ont bien assisté. Importe cette liste avant ou juste après le live J{dayNumber}.</p>
            {editionState && (
              <p className="text-amber-300">
                Actuellement en DB pour J{dayNumber} : {editionState.day_stats[`day${dayNumber}`]?.registered ?? 0} inscrits StreamYard enregistrés.
              </p>
            )}
          </div>

          <div className="flex gap-2">
            {(["paste", "csv"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setRegistrantsMode(mode)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  registrantsMode === mode
                    ? "bg-emerald-500 text-zinc-950"
                    : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                }`}
              >
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
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono"
            />
          ) : (
            <label className="block border border-dashed border-zinc-700 rounded-xl px-4 py-6 bg-zinc-950 cursor-pointer hover:border-emerald-500/40 transition-colors">
              <div className="flex items-center gap-3">
                <UploadSimple size={20} className="text-zinc-500" />
                <div>
                  <p className="text-sm font-medium text-zinc-200">Importer un CSV StreamYard</p>
                  <p className="text-xs text-zinc-500 mt-1">{registrantsFileName || "Sélectionne un fichier .csv"}</p>
                </div>
              </div>
              <input type="file" accept=".csv,text/csv" className="hidden" onChange={async (e) => {
                const file = e.target.files?.[0];
                if (file) await handleCsvFile(file, "registrants");
              }} />
            </label>
          )}

          <p className="text-xs text-zinc-500">
            Numéros détectés : <span className="text-zinc-300 font-mono">
              {registrantsMode === "paste" ? extractPhonesFromText(registrantsText).length : registrantsPhones.length}
            </span>
          </p>
          <button
            onClick={() => submitPhoneBatch("registrants")}
            disabled={submitting !== null}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-950 font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
          >
            {submitting === "registrants" ? "Envoi…" : `Enregistrer les inscrits J${dayNumber}`}
          </button>
          <Alert state={registrantsState} />
        </SectionCard>

        {/* ── 3. Présents live ─────────────────────────────────────────────── */}
        <SectionCard
          title="3. Après le live — Présents"
          description="Envoie la liste des contacts qui ont participé au live. Cela active le template attended pour le broadcast J+1."
          icon={<CheckCircle size={16} className="text-zinc-400" />}
        >
          <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl px-4 py-3 text-xs text-blue-300 space-y-1">
            <p className="font-semibold">Pourquoi c'est critique</p>
            <p>Sans cette liste, personne ne reçoit le message <code>attended_v2</code> le lendemain — même les contacts qui étaient bien présents. Importe cette liste dans les heures qui suivent le live.</p>
            {editionState && (
              <p className="text-blue-200">
                Actuellement en DB pour J{dayNumber} : {editionState.day_stats[`day${dayNumber}`]?.attended ?? 0} présents enregistrés.
              </p>
            )}
          </div>

          <div className="flex gap-2">
            {(["paste", "csv"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setAttendanceMode(mode)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  attendanceMode === mode
                    ? "bg-emerald-500 text-zinc-950"
                    : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                }`}
              >
                {mode === "paste" ? "Coller les numéros" : "Importer un CSV"}
              </button>
            ))}
          </div>

          {attendanceMode === "paste" ? (
            <textarea
              value={attendanceText}
              onChange={(e) => setAttendanceText(e.target.value)}
              rows={6}
              placeholder={"Un numéro par ligne\n22901020304\n+447507135074"}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50 font-mono"
            />
          ) : (
            <label className="block border border-dashed border-zinc-700 rounded-xl px-4 py-6 bg-zinc-950 cursor-pointer hover:border-emerald-500/40 transition-colors">
              <div className="flex items-center gap-3">
                <UploadSimple size={20} className="text-zinc-500" />
                <div>
                  <p className="text-sm font-medium text-zinc-200">Importer un CSV StreamYard</p>
                  <p className="text-xs text-zinc-500 mt-1">{attendanceFileName || "Sélectionne un fichier .csv"}</p>
                </div>
              </div>
              <input type="file" accept=".csv,text/csv" className="hidden" onChange={async (e) => {
                const file = e.target.files?.[0];
                if (file) await handleCsvFile(file, "attendance");
              }} />
            </label>
          )}

          <p className="text-xs text-zinc-500">
            Numéros détectés : <span className="text-zinc-300 font-mono">
              {attendanceMode === "paste" ? extractPhonesFromText(attendanceText).length : attendancePhones.length}
            </span>
          </p>
          <button
            onClick={() => submitPhoneBatch("attendance")}
            disabled={submitting !== null}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-950 font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
          >
            {submitting === "attendance" ? "Envoi…" : `Enregistrer les présents J${dayNumber}`}
          </button>
          <Alert state={attendanceState} />
        </SectionCard>

      </div>
    </div>
  );
}
