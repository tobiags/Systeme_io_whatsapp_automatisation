import { useMemo, useState, type ReactNode } from "react";
import { CalendarCheck, CheckCircle, UploadSimple, WarningCircle } from "@phosphor-icons/react";

const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

type Cohort = "EU" | "US-CA";
type SyncMode = "paste" | "csv";

interface ActionState {
  kind: "idle" | "success" | "error";
  message: string;
}

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

function Alert({ state }: { state: ActionState }) {
  if (state.kind === "idle") return null;
  const isSuccess = state.kind === "success";
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm flex items-start gap-3 ${
      isSuccess
        ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-300"
        : "bg-red-500/5 border-red-500/20 text-red-300"
    }`}>
      {isSuccess ? <CheckCircle size={18} weight="fill" className="shrink-0 mt-0.5" /> : <WarningCircle size={18} weight="fill" className="shrink-0 mt-0.5" />}
      <span>{state.message}</span>
    </div>
  );
}

function SectionCard({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 md:p-6 space-y-5">
      <div>
        <h2 className="text-base md:text-lg font-bold text-zinc-100">{title}</h2>
        <p className="text-sm text-zinc-500 mt-1">{description}</p>
      </div>
      {children}
    </section>
  );
}

export default function StreamyardOpsPage() {
  const token = useMemo(() => new URLSearchParams(window.location.search).get("token")?.trim() ?? "", []);

  const [cohort, setCohort] = useState<Cohort>("US-CA");
  const [editionKey, setEditionKey] = useState("");
  const [dayNumber, setDayNumber] = useState("1");
  const [joinUrl, setJoinUrl] = useState("");

  const [registrantsMode, setRegistrantsMode] = useState<SyncMode>("paste");
  const [registrantsText, setRegistrantsText] = useState("");
  const [registrantsFileName, setRegistrantsFileName] = useState("");
  const [registrantsPhones, setRegistrantsPhones] = useState<string[]>([]);

  const [attendanceMode, setAttendanceMode] = useState<SyncMode>("paste");
  const [attendanceText, setAttendanceText] = useState("");
  const [attendanceFileName, setAttendanceFileName] = useState("");
  const [attendancePhones, setAttendancePhones] = useState<string[]>([]);

  const [sessionState, setSessionState] = useState<ActionState>({ kind: "idle", message: "" });
  const [registrantsState, setRegistrantsState] = useState<ActionState>({ kind: "idle", message: "" });
  const [attendanceState, setAttendanceState] = useState<ActionState>({ kind: "idle", message: "" });
  const [submitting, setSubmitting] = useState<null | "session" | "registrants" | "attendance">(null);

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

  async function submitSession() {
    if (!editionKey.trim() || !joinUrl.trim()) {
      setSessionState({ kind: "error", message: "Renseigne l'édition et le lien StreamYard avant de valider." });
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
        message: `Live enregistré pour ${data.region} / jour ${data.day_number}. Les rappels utiliseront maintenant ce lien.`,
      });
    } catch (error) {
      setSessionState({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
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
    if (!editionKey.trim()) {
      const setter = target === "registrants" ? setRegistrantsState : setAttendanceState;
      setter({ kind: "error", message: "Renseigne d'abord l'édition et le jour du live." });
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
            ? `${data.recorded} inscrit(s) enregistrés, ${data.already_recorded} déjà connus, ${data.not_found} non trouvés.`
            : `${data.recorded} présent(s) enregistrés, ${data.already_recorded} déjà connus, ${data.not_found} non trouvés.`,
      });
    } catch (error) {
      stateSetter({ kind: "error", message: error instanceof Error ? error.message : "Erreur inconnue." });
    } finally {
      setSubmitting(null);
    }
  }

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

  return (
    <div className="min-h-[100dvh] bg-zinc-950 text-zinc-100 px-4 py-6 md:px-8 md:py-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 md:p-6">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
              <CalendarCheck size={20} weight="fill" className="text-emerald-400" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-500 font-semibold">Opérations StreamYard</p>
              <h1 className="text-xl md:text-2xl font-bold text-zinc-100 mt-1">Pilotage live sans Termius</h1>
              <p className="text-sm text-zinc-400 mt-2">
                Remplis les infos du live, puis envoie les inscrits et les présents. La plateforme se charge du reste.
              </p>
            </div>
          </div>
        </div>

        <SectionCard
          title="Contexte du live"
          description="Ces champs servent aux trois actions ci-dessous. Renseigne-les une seule fois, puis enchaîne."
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <label className="block">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Cohorte</span>
              <select
                value={cohort}
                onChange={(e) => setCohort(e.target.value as Cohort)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50"
              >
                <option value="US-CA">US/CA</option>
                <option value="EU">EU</option>
              </select>
            </label>
            <label className="block md:col-span-2">
              <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Edition key</span>
              <input
                value={editionKey}
                onChange={(e) => setEditionKey(e.target.value)}
                placeholder="2026-05-22-usca"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50"
              />
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

        <SectionCard
          title="1. Avant le live"
          description="Renseigne le lien StreamYard du jour pour que les messages de rappel utilisent la bonne URL."
        >
          <label className="block">
            <span className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-2">Lien StreamYard</span>
            <input
              value={joinUrl}
              onChange={(e) => setJoinUrl(e.target.value)}
              placeholder="https://streamyard.com/watch/..."
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50"
            />
          </label>
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            <button
              onClick={submitSession}
              disabled={submitting !== null}
              className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-950 font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
            >
              {submitting === "session" ? "Enregistrement..." : "Enregistrer le live"}
            </button>
            <p className="text-xs text-zinc-500">À faire une fois par cohorte et par jour.</p>
          </div>
          <Alert state={sessionState} />
        </SectionCard>

        <SectionCard
          title="2. Juste avant / au début"
          description="Envoie la liste des inscrits StreamYard. Tu peux coller les numéros ou importer un CSV."
        >
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
              rows={7}
              placeholder={"Un numéro par ligne\n22901020304\n+447507135074"}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50"
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
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) await handleCsvFile(file, "registrants");
                }}
              />
            </label>
          )}
          <p className="text-xs text-zinc-500">
            Numéros détectés : {registrantsMode === "paste" ? extractPhonesFromText(registrantsText).length : registrantsPhones.length}
          </p>
          <button
            onClick={() => submitPhoneBatch("registrants")}
            disabled={submitting !== null}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-950 font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
          >
            {submitting === "registrants" ? "Envoi..." : "Envoyer les inscrits"}
          </button>
          <Alert state={registrantsState} />
        </SectionCard>

        <SectionCard
          title="3. Après le live"
          description="Envoie la liste des présents live pour déclencher les bonnes relances J2/J3 et post-challenge."
        >
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
              rows={7}
              placeholder={"Un numéro par ligne\n22901020304\n+447507135074"}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-3 text-sm focus:outline-none focus:border-emerald-500/50"
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
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) await handleCsvFile(file, "attendance");
                }}
              />
            </label>
          )}
          <p className="text-xs text-zinc-500">
            Numéros détectés : {attendanceMode === "paste" ? extractPhonesFromText(attendanceText).length : attendancePhones.length}
          </p>
          <button
            onClick={() => submitPhoneBatch("attendance")}
            disabled={submitting !== null}
            className="bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-zinc-950 font-semibold text-sm px-4 py-3 rounded-xl transition-colors"
          >
            {submitting === "attendance" ? "Envoi..." : "Envoyer les présents"}
          </button>
          <Alert state={attendanceState} />
        </SectionCard>
      </div>
    </div>
  );
}
