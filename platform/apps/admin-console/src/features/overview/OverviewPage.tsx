import { useEffect, useState, useCallback } from "react";
import {
  Users, ChatCircle, Warning, TrendUp,
  CalendarCheck, ArrowClockwise, Lightning,
  Siren, CheckCircle, Clock, Robot,
} from "@phosphor-icons/react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Summary {
  contacts_total: number;
  messages_sent_total: number;
  campaigns_active: number;
  manual_followups: number;
  conversion_rate: number;
  contacts_by_segment: Record<string, number>;
  contacts_by_cohort: Record<string, number>;
  active_edition: { edition_key: string; cohort: string; edition_date: string; streamyard_url: string | null } | null;
  live_attendance_by_day: Record<string, number>;
  faq_counts: Record<string, number>;
  financial_objections_total: number;
  financial_objections_by_type: Record<string, number>;
}

interface QueueItem {
  id: number;
  phone: string;
  contact_id: string | null;
  text: string;
  ai_reply: string | null;
  intent: string;
  priority: "haute" | "moyenne" | "faible";
  received_at: string;
}

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

// ── Config ─────────────────────────────────────────────────────────────────────

const SEGMENT_CONFIG: Record<string, { label: string; color: string; bar: string }> = {
  froid:      { label: "Froid",      color: "text-blue-400",   bar: "bg-blue-500" },
  tiede:      { label: "Tiède",      color: "text-amber-400",  bar: "bg-amber-500" },
  chaud:      { label: "Chaud",      color: "text-orange-400", bar: "bg-orange-500" },
  tres_chaud: { label: "Très chaud", color: "text-red-400",    bar: "bg-red-500" },
};

const PRIORITY_CONFIG = {
  haute:   { label: "Haute",   cls: "bg-red-500/10 text-red-400 border border-red-500/20" },
  moyenne: { label: "Moyenne", cls: "bg-amber-500/10 text-amber-400 border border-amber-500/20" },
  faible:  { label: "Faible",  cls: "bg-zinc-800 text-zinc-400 border border-zinc-700" },
};

const INTENT_LABELS: Record<string, string> = {
  human_escalation: "Escalade humaine",
  payment_failure_followup_needed: "Echec paiement",
  installment_plan_request: "Plan de paiement",
  skeptic_trust_objection: "Objection confiance",
  objection_financial_strong: "Objection financiere forte",
  objection_financial_soft: "Objection financiere",
  faq_start_time: "FAQ Horaires",
  faq_email_missing: "FAQ Email manquant",
  faq_offer_price: "FAQ Prix",
  faq_whatsapp_group_join: "FAQ Groupe WA",
  faq_next_challenge_date: "FAQ Prochaine edition",
  next_challenge_request: "Prochain challenge",
  ai_generated: "IA generique",
  default: "Autre",
};

// ── Utils ──────────────────────────────────────────────────────────────────────

function fmt(n: number) { return new Intl.NumberFormat("fr-FR").format(n); }
function fmtPct(n: number) { return `${(n * 100).toFixed(1)} %`; }
function fmtDate(s: string) {
  return new Date(s).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skel({ className = "" }: { className?: string }) {
  return <div className={`bg-zinc-800 animate-pulse rounded-lg ${className}`} />;
}

// ── Bar row ───────────────────────────────────────────────────────────────────

function BarRow({ label, count, max, barColor, labelColor, delay }: {
  label: string; count: number; max: number;
  barColor: string; labelColor?: string; delay: string;
}) {
  const pct = max > 0 ? (count / max) * 100 : 0;
  return (
    <div className={`fade-in ${delay}`}>
      <div className="flex justify-between items-baseline mb-1.5">
        <span className={`text-xs font-semibold uppercase tracking-wider ${labelColor ?? "text-zinc-400"}`}>{label}</span>
        <span className="font-mono text-sm font-bold text-zinc-100">{fmt(count)}</span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full ${barColor} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, icon: Icon, iconClass, delay }: {
  label: string; value: string; sub: string;
  icon: React.ElementType; iconClass: string; delay: string;
}) {
  return (
    <div className={`bg-zinc-900 border border-zinc-800 rounded-xl p-5 hover:border-zinc-700 transition-colors fade-in ${delay}`}>
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-4 ${iconClass}`}>
        <Icon size={18} weight="duotone" />
      </div>
      <p className="font-mono text-3xl font-bold text-zinc-100 tracking-tight leading-none">{value}</p>
      <p className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mt-2">{label}</p>
      <p className="text-xs text-zinc-600 mt-0.5">{sub}</p>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function OverviewPage({ apiKey }: { apiKey: string }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const hdrs: HeadersInit = apiKey ? { "X-API-Key": apiKey } : {};
  const refresh = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetch(`${API_BASE}/dashboard/summary`, { headers: hdrs }).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Summary>;
      }),
      fetch(`${API_BASE}/webhooks/wati/queue`, { headers: hdrs }).then((r) => {
        if (!r.ok) return [] as QueueItem[];
        return r.json() as Promise<QueueItem[]>;
      }),
    ])
      .then(([s, q]) => { setSummary(s); setQueue(q); })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [tick, apiKey]);

  // Auto-refresh 60 s
  useEffect(() => {
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
  }, [refresh]);

  const maxSeg = Math.max(1, ...Object.values(summary?.contacts_by_segment ?? {}));
  const maxDay = Math.max(1, ...Object.values(summary?.live_attendance_by_day ?? {}));
  const maxFaq = Math.max(1, ...Object.values(summary?.faq_counts ?? {}));

  return (
    <div className="space-y-8">

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400 fade-in">
          <Warning size={16} weight="fill" />
          Erreur API : {error}
        </div>
      )}

      {/* Edition banner */}
      {!loading && summary?.active_edition && (
        <div className="flex items-center justify-between bg-emerald-500/5 border border-emerald-500/20 rounded-xl px-5 py-3 fade-in">
          <div className="flex items-center gap-3">
            <CalendarCheck size={18} weight="duotone" className="text-emerald-400" />
            <span className="text-xs text-zinc-500 font-semibold uppercase tracking-wider">Edition active</span>
            <span className="text-sm font-bold text-zinc-100">{summary.active_edition.edition_key}</span>
            <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-md">{summary.active_edition.cohort}</span>
          </div>
          {summary.active_edition.streamyard_url && (
            <a href={summary.active_edition.streamyard_url} target="_blank" rel="noreferrer"
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors">
              Lien StreamYard
            </a>
          )}
        </div>
      )}

      {/* KPI row */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">Vue d'ensemble</h2>
          <button onClick={refresh} className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
            <ArrowClockwise size={13} />
            Rafraichir
          </button>
        </div>
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <Skel key={i} className="h-36" />)}
          </div>
        ) : summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Contacts" value={fmt(summary.contacts_total)} sub="inscrits au total"
              icon={Users} iconClass="bg-blue-500/10 text-blue-400" delay="stagger-1" />
            <StatCard label="Messages envoyes" value={fmt(summary.messages_sent_total)} sub="tous statuts"
              icon={ChatCircle} iconClass="bg-emerald-500/10 text-emerald-400" delay="stagger-2" />
            <StatCard label="Relances humaines" value={fmt(summary.manual_followups)} sub="en attente"
              icon={Warning} iconClass={summary.manual_followups > 0 ? "bg-red-500/10 text-red-400" : "bg-zinc-800 text-zinc-500"}
              delay="stagger-3" />
            <StatCard label="Conversion" value={fmtPct(summary.conversion_rate)} sub="contacts ayant achete"
              icon={TrendUp} iconClass="bg-violet-500/10 text-violet-400" delay="stagger-4" />
          </div>
        )}
      </section>

      {/* Attendance + Segments */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 fade-in">
          <h2 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-5">Presence live par jour</h2>
          {loading ? <div className="space-y-4">{[...Array(3)].map((_, i) => <Skel key={i} className="h-10" />)}</div> : (
            <div className="space-y-4">
              {(["day1", "day2", "day3"] as const).map((d, i) => (
                <BarRow key={d} label={`Jour ${i + 1}`}
                  count={summary?.live_attendance_by_day[d] ?? 0}
                  max={maxDay} barColor="bg-emerald-500"
                  delay={`stagger-${i + 1}`} />
              ))}
            </div>
          )}
        </section>

        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 fade-in">
          <h2 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-5">Segments</h2>
          {loading ? <div className="space-y-4">{[...Array(4)].map((_, i) => <Skel key={i} className="h-10" />)}</div> : (
            <div className="space-y-4">
              {Object.entries(SEGMENT_CONFIG).map(([k, cfg], i) => (
                <BarRow key={k} label={cfg.label}
                  count={summary?.contacts_by_segment[k] ?? 0}
                  max={maxSeg} barColor={cfg.bar} labelColor={cfg.color}
                  delay={`stagger-${i + 1}`} />
              ))}
            </div>
          )}
        </section>
      </div>

      {/* FAQ + Objections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 fade-in">
          <div className="flex items-center gap-2 mb-5">
            <Robot size={14} className="text-zinc-500" />
            <h2 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">FAQ detectees</h2>
          </div>
          {loading ? <div className="space-y-3">{[...Array(4)].map((_, i) => <Skel key={i} className="h-8" />)}</div> :
            Object.keys(summary?.faq_counts ?? {}).length === 0
              ? <p className="text-sm text-zinc-600 py-4">Aucune FAQ enregistree</p>
              : <div className="space-y-3">
                {Object.entries(summary?.faq_counts ?? {}).sort((a, b) => b[1] - a[1]).map(([intent, count], i) => (
                  <BarRow key={intent} label={INTENT_LABELS[intent] ?? intent}
                    count={count} max={maxFaq} barColor="bg-blue-500"
                    delay={`stagger-${Math.min(i + 1, 4)}`} />
                ))}
              </div>
          }
        </section>

        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 fade-in">
          <div className="flex items-center gap-2 mb-5">
            <Lightning size={14} className="text-zinc-500" />
            <h2 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">Objections financieres</h2>
          </div>
          {loading ? <div className="space-y-3">{[...Array(4)].map((_, i) => <Skel key={i} className="h-8" />)}</div> : (
            <>
              {(summary?.financial_objections_total ?? 0) > 0 && (
                <p className="font-mono text-2xl font-bold text-zinc-100 mb-4">
                  {fmt(summary!.financial_objections_total)}
                  <span className="text-xs text-zinc-600 font-normal ml-2">total</span>
                </p>
              )}
              {Object.keys(summary?.financial_objections_by_type ?? {}).length === 0
                ? <p className="text-sm text-zinc-600 py-2">Aucune objection enregistree</p>
                : <div className="divide-y divide-zinc-800">
                  {Object.entries(summary?.financial_objections_by_type ?? {}).sort((a, b) => b[1] - a[1]).map(([intent, count]) => (
                    <div key={intent} className="flex items-center justify-between py-2.5">
                      <span className="text-xs text-zinc-400 truncate">{INTENT_LABELS[intent] ?? intent}</span>
                      <span className="font-mono text-xs font-bold text-amber-400 ml-3 shrink-0">{count}</span>
                    </div>
                  ))}
                </div>
              }
            </>
          )}
        </section>
      </div>

      {/* Cohorts */}
      {!loading && summary && Object.keys(summary.contacts_by_cohort).length > 0 && (
        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 fade-in">
          <h2 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest mb-4">Cohortes</h2>
          <div className="flex gap-8">
            {Object.entries(summary.contacts_by_cohort).map(([cohort, count]) => (
              <div key={cohort}>
                <p className="font-mono text-2xl font-bold text-zinc-100">{fmt(count)}</p>
                <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mt-1">{cohort}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Human queue */}
      <section className="fade-in">
        <div className="flex items-center gap-2 mb-4">
          <Siren size={14} className="text-zinc-500" />
          <h2 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">File de relances humaines</h2>
          {queue.length > 0 && (
            <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none">{queue.length}</span>
          )}
        </div>

        {loading ? (
          <div className="space-y-2">{[...Array(3)].map((_, i) => <Skel key={i} className="h-14" />)}</div>
        ) : queue.length === 0 ? (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl px-6 py-12 flex flex-col items-center gap-3">
            <CheckCircle size={36} weight="duotone" className="text-emerald-500" />
            <p className="text-sm text-zinc-400 font-medium">Aucune relance en attente</p>
          </div>
        ) : (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800">
                  {["Priorite", "Tel", "Message", "Reponse IA", "Intention", "Recu le"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-[11px] font-bold text-zinc-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {queue.map((msg) => {
                  const p = PRIORITY_CONFIG[msg.priority] ?? PRIORITY_CONFIG.faible;
                  return (
                    <tr key={msg.id} className="hover:bg-zinc-800/40 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${p.cls}`}>{p.label}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap font-mono text-xs text-zinc-300">{msg.phone}</td>
                      <td className="px-4 py-3 max-w-[200px]">
                        <p className="text-xs text-zinc-300 line-clamp-2">{msg.text}</p>
                      </td>
                      <td className="px-4 py-3 max-w-[200px]">
                        <p className="text-xs text-zinc-500 line-clamp-2">{msg.ai_reply ?? "—"}</p>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-xs text-zinc-400">{INTENT_LABELS[msg.intent] ?? msg.intent}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="flex items-center gap-1 text-xs text-zinc-600">
                          <Clock size={11} />
                          {fmtDate(msg.received_at)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
