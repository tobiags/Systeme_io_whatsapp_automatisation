import { useEffect, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Summary {
  contacts_total: number;
  campaigns_active: number;
  manual_followups: number;
  conversion_rate: number;
  contacts_by_segment: Record<string, number>;
  contacts_by_cohort: Record<string, number>;
}

interface InboundMessage {
  id: number;
  phone: string;
  contact_id: string | null;
  text: string;
  ai_reply: string | null;
  intent: string;
  received_at: string;
}

// ── Config ────────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

// ── Styles ────────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  section: { marginBottom: "40px" },
  sectionTitle: { fontSize: "18px", fontWeight: 700, color: "#2d3748", marginBottom: "16px", borderBottom: "2px solid #e2e8f0", paddingBottom: "8px" },
  kpiGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "16px" },
  kpiCard: { background: "#fff", borderRadius: "12px", padding: "20px", boxShadow: "0 1px 4px rgba(0,0,0,.08)", display: "flex", flexDirection: "column" as const, gap: "8px" },
  kpiLabel: { fontSize: "12px", fontWeight: 600, color: "#718096", textTransform: "uppercase" as const, letterSpacing: "0.08em" },
  kpiValue: { fontSize: "36px", fontWeight: 800, color: "#1a365d" },
  kpiSub: { fontSize: "13px", color: "#718096" },
  segGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "12px" },
  segCard: { background: "#fff", borderRadius: "10px", padding: "16px", boxShadow: "0 1px 4px rgba(0,0,0,.06)", textAlign: "center" as const },
  segLabel: { fontSize: "12px", fontWeight: 600, color: "#718096", textTransform: "uppercase" as const, letterSpacing: "0.06em", marginBottom: "8px" },
  segCount: { fontSize: "28px", fontWeight: 800 },
  table: { width: "100%", borderCollapse: "collapse" as const, background: "#fff", borderRadius: "10px", overflow: "hidden", boxShadow: "0 1px 4px rgba(0,0,0,.06)" },
  th: { background: "#f7fafc", padding: "10px 14px", textAlign: "left" as const, fontSize: "12px", fontWeight: 700, color: "#4a5568", textTransform: "uppercase" as const, letterSpacing: "0.05em" },
  td: { padding: "10px 14px", fontSize: "14px", borderTop: "1px solid #e2e8f0", color: "#2d3748", verticalAlign: "top" as const },
  badge: { display: "inline-block", padding: "2px 8px", borderRadius: "999px", fontSize: "12px", fontWeight: 600 },
  error: { color: "#e53e3e", padding: "16px", background: "#fff5f5", borderRadius: "8px", marginBottom: "24px" },
  loader: { color: "#718096", padding: "32px", textAlign: "center" as const },
  refresh: { marginLeft: "12px", fontSize: "13px", color: "#3182ce", cursor: "pointer", background: "none", border: "none", padding: "0" },
};

const SEGMENT_COLORS: Record<string, string> = {
  froid: "#bee3f8",
  tiede: "#fbd38d",
  chaud: "#feb2b2",
  tres_chaud: "#fc8181",
};

const SEGMENT_LABELS: Record<string, string> = {
  froid: "❄️ Froid",
  tiede: "🌤 Tiède",
  chaud: "🔥 Chaud",
  tres_chaud: "🚀 Très chaud",
};

const INTENT_BADGE: Record<string, { bg: string; color: string }> = {
  faq: { bg: "#c6f6d5", color: "#276749" },
  human_escalation: { bg: "#fed7d7", color: "#9b2c2c" },
  financial_objection: { bg: "#fefcbf", color: "#744210" },
  ai_generated: { bg: "#bee3f8", color: "#2c5282" },
  default: { bg: "#e2e8f0", color: "#4a5568" },
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function OverviewPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [queue, setQueue] = useState<InboundMessage[]>([]);
  const [loadingSum, setLoadingSum] = useState(true);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setLoadingSum(true);
    fetch(`${API_BASE}/dashboard/summary`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setSummary)
      .catch((e) => setError(String(e)))
      .finally(() => setLoadingSum(false));
  }, [tick]);

  useEffect(() => {
    setLoadingQueue(true);
    fetch(`${API_BASE}/webhooks/wati/queue`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setQueue)
      .catch(() => {}) // non-blocking
      .finally(() => setLoadingQueue(false));
  }, [tick]);

  const refresh = () => setTick((t) => t + 1);

  return (
    <div>
      {error && <div style={s.error}>⚠️ Erreur API : {error}</div>}

      {/* ── KPI cards ─────────────────────────────────────────────────────── */}
      <section style={s.section}>
        <h2 style={s.sectionTitle}>
          Vue d'ensemble
          <button style={s.refresh} onClick={refresh}>↻ Rafraîchir</button>
        </h2>
        {loadingSum ? (
          <div style={s.loader}>Chargement…</div>
        ) : summary ? (
          <div style={s.kpiGrid}>
            <KpiCard label="Contacts" value={summary.contacts_total} sub="inscrits au total" color="#3182ce" />
            <KpiCard label="Campagnes actives" value={summary.campaigns_active} sub="challenges en cours" color="#805ad5" />
            <KpiCard label="Relances humaines" value={summary.manual_followups} sub="messages en attente" color="#e53e3e" />
            <KpiCard
              label="Taux conversion"
              value={`${(summary.conversion_rate * 100).toFixed(1)}%`}
              sub="contacts ayant acheté"
              color="#38a169"
            />
          </div>
        ) : null}
      </section>

      {/* ── Segment breakdown ─────────────────────────────────────────────── */}
      {summary && (
        <section style={s.section}>
          <h2 style={s.sectionTitle}>Répartition par segment</h2>
          <div style={s.segGrid}>
            {Object.entries(summary.contacts_by_segment).map(([seg, count]) => (
              <div key={seg} style={{ ...s.segCard, borderTop: `4px solid ${SEGMENT_COLORS[seg] ?? "#e2e8f0"}` }}>
                <div style={s.segLabel}>{SEGMENT_LABELS[seg] ?? seg}</div>
                <div style={{ ...s.segCount, color: "#1a365d" }}>{count}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Cohort breakdown ──────────────────────────────────────────────── */}
      {summary && Object.keys(summary.contacts_by_cohort).length > 0 && (
        <section style={s.section}>
          <h2 style={s.sectionTitle}>Répartition par cohorte</h2>
          <div style={s.segGrid}>
            {Object.entries(summary.contacts_by_cohort).map(([cohort, count]) => (
              <div key={cohort} style={{ ...s.segCard, borderTop: "4px solid #90cdf4" }}>
                <div style={s.segLabel}>🌍 {cohort}</div>
                <div style={{ ...s.segCount, color: "#1a365d" }}>{count}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Human follow-up queue ─────────────────────────────────────────── */}
      <section style={s.section}>
        <h2 style={s.sectionTitle}>
          🆘 File de relances humaines
          {queue.length > 0 && (
            <span style={{ marginLeft: "8px", background: "#e53e3e", color: "#fff", fontSize: "12px", borderRadius: "999px", padding: "2px 8px", fontWeight: 700 }}>
              {queue.length}
            </span>
          )}
        </h2>
        {loadingQueue ? (
          <div style={s.loader}>Chargement…</div>
        ) : queue.length === 0 ? (
          <div style={{ ...s.loader, color: "#38a169" }}>✅ Aucune relance en attente</div>
        ) : (
          <table style={s.table}>
            <thead>
              <tr>
                {["Téléphone", "Contact ID", "Message", "Réponse IA", "Intention", "Reçu le"].map((h) => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {queue.map((msg) => {
                const intentStyle = INTENT_BADGE[msg.intent] ?? INTENT_BADGE.default;
                return (
                  <tr key={msg.id}>
                    <td style={s.td}>{msg.phone}</td>
                    <td style={s.td}>{msg.contact_id ?? <span style={{ color: "#a0aec0" }}>inconnu</span>}</td>
                    <td style={{ ...s.td, maxWidth: "240px" }}>{msg.text}</td>
                    <td style={{ ...s.td, maxWidth: "240px", color: "#718096" }}>{msg.ai_reply ?? "—"}</td>
                    <td style={s.td}>
                      <span style={{ ...s.badge, background: intentStyle.bg, color: intentStyle.color }}>
                        {msg.intent}
                      </span>
                    </td>
                    <td style={{ ...s.td, whiteSpace: "nowrap" as const, color: "#718096" }}>
                      {new Date(msg.received_at).toLocaleString("fr-FR")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color }: { label: string; value: number | string; sub: string; color: string }) {
  return (
    <div style={{ ...s.kpiCard, borderTop: `4px solid ${color}` }}>
      <div style={s.kpiLabel}>{label}</div>
      <div style={{ ...s.kpiValue, color }}>{value}</div>
      <div style={s.kpiSub}>{sub}</div>
    </div>
  );
}
