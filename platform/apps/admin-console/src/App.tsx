import { useState } from "react";
import { LockKey, WhatsappLogo } from "@phosphor-icons/react";
import OverviewPage from "./features/overview/OverviewPage";

const STORAGE_KEY = "wfba_api_key";

function AuthGate({ onAuth }: { onAuth: (key: string) => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const k = value.trim();
    if (!k) { setError(true); return; }
    localStorage.setItem(STORAGE_KEY, k);
    onAuth(k);
  };

  return (
    <div className="min-h-[100dvh] bg-zinc-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm fade-in">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <WhatsappLogo size={20} weight="fill" className="text-emerald-400" />
          </div>
          <div>
            <p className="text-xs text-zinc-500 uppercase tracking-widest font-semibold">Challenge Amazon FBA</p>
            <p className="text-sm font-semibold text-zinc-100">Console Admin</p>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-400 mb-2 uppercase tracking-wider">
              Clé API
            </label>
            <div className="relative">
              <LockKey size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="password"
                value={value}
                onChange={(e) => { setValue(e.target.value); setError(false); }}
                placeholder="PLATFORM_API_KEY"
                className={`w-full bg-zinc-900 border ${error ? "border-red-500/60" : "border-zinc-800"} rounded-lg pl-9 pr-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/50 transition-colors font-mono`}
                autoFocus
              />
            </div>
            {error && <p className="mt-1.5 text-xs text-red-400">Clé requise</p>}
          </div>
          <button
            type="submit"
            className="w-full bg-emerald-500 hover:bg-emerald-400 active:scale-[0.98] text-zinc-950 font-semibold text-sm py-3 rounded-lg transition-all duration-150"
          >
            Accéder au dashboard
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-zinc-600">
          Valeur de <code className="text-zinc-500">PLATFORM_API_KEY</code> dans Coolify
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem(STORAGE_KEY) ?? "");

  if (!apiKey) return <AuthGate onAuth={setApiKey} />;

  return (
    <div className="min-h-[100dvh] bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-800/80 px-6 py-3 flex items-center justify-between sticky top-0 bg-zinc-950/90 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <WhatsappLogo size={16} weight="fill" className="text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-bold text-zinc-100 tracking-tight">Challenge Amazon FBA</span>
            <span className="text-xs text-zinc-500">Console Admin</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-zinc-400 font-medium">En ligne</span>
          <button
            onClick={() => { localStorage.removeItem(STORAGE_KEY); setApiKey(""); }}
            className="ml-4 text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
          >
            Déconnexion
          </button>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-6 py-8">
        <OverviewPage apiKey={apiKey} />
      </main>
    </div>
  );
}
