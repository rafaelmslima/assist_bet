import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  AlertTriangle,
  CalendarDays,
  ChevronRight,
  Clock,
  LogOut,
  RefreshCw,
  Search,
  Shield,
  Users
} from "lucide-react";
import { api } from "./api";
import { AnalysisPayload, Fixture, FixtureList, League, Tab, User, tabs } from "./types";

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    api<User>("/api/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setBooting(false));
  }, []);

  if (booting) {
    return <div className="boot">Carregando dashboard...</div>;
  }

  if (!user) {
    return <LoginScreen onLogin={setUser} />;
  }

  return <Dashboard user={user} onLogout={() => setUser(null)} />;
}

function LoginScreen({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const user = await api<User>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      onLogin(user);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Falha no login.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <form className="login-panel" onSubmit={submit}>
        <div className="brand-row">
          <Shield size={24} />
          <span>Assist Bet</span>
        </div>
        <h1>Dashboard</h1>
        <label>
          Email
          <input autoFocus value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
        </label>
        <label>
          Senha
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button className="primary-button" disabled={loading} type="submit">
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </main>
  );
}

function Dashboard({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [selectedLeague, setSelectedLeague] = useState("");
  const [dateMode, setDateMode] = useState("today");
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [selectedFixture, setSelectedFixture] = useState<Fixture | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisPayload | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Analise IA");
  const [loadingFixtures, setLoadingFixtures] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<League[]>("/api/leagues")
      .then((items) => {
        setLeagues(items);
        setSelectedLeague(items[0]?.key || "");
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Falha ao carregar ligas."));
  }, []);

  useEffect(() => {
    if (!selectedLeague) return;
    refreshFixtures();
  }, [selectedLeague, dateMode]);

  async function refreshFixtures() {
    setLoadingFixtures(true);
    setError("");
    setAnalysis(null);
    setSelectedFixture(null);
    try {
      const result = await api<FixtureList>(
        `/api/fixtures?date=${encodeURIComponent(dateMode)}&league_key=${encodeURIComponent(selectedLeague)}`
      );
      if (!result.ok) {
        setError(result.error || "Nao encontrei jogos para esse filtro.");
      }
      setFixtures(result.fixtures || []);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Falha ao carregar jogos.");
      setFixtures([]);
    } finally {
      setLoadingFixtures(false);
    }
  }

  async function selectFixture(fixture: Fixture) {
    setSelectedFixture(fixture);
    setActiveTab("Analise IA");
    setLoadingAnalysis(true);
    setAnalysis(null);
    setError("");
    try {
      const payload = await api<AnalysisPayload>(`/api/fixtures/${fixture.fixture_id}/analysis`);
      setAnalysis(payload);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Falha ao gerar analise.");
    } finally {
      setLoadingAnalysis(false);
    }
  }

  async function logout() {
    await api<{ ok: boolean }>("/api/auth/logout", { method: "POST" }).catch(() => null);
    onLogout();
  }

  const currentLeague = useMemo(() => leagues.find((item) => item.key === selectedLeague), [leagues, selectedLeague]);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="brand-row">
            <Shield size={22} />
            <span>Assist Bet</span>
          </div>
          <button className="icon-button" onClick={logout} title="Sair" type="button">
            <LogOut size={18} />
          </button>
        </div>

        <section className="filters">
          <label>
            Liga
            <select value={selectedLeague} onChange={(event) => setSelectedLeague(event.target.value)}>
              {leagues.map((league) => (
                <option key={league.key} value={league.key}>
                  {league.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Data
            <select value={dateMode} onChange={(event) => setDateMode(event.target.value)}>
              <option value="today">Hoje</option>
              <option value="tomorrow">Amanha</option>
            </select>
          </label>
          <button className="secondary-button" onClick={refreshFixtures} type="button">
            <RefreshCw size={16} />
            Atualizar
          </button>
        </section>

        <div className="user-strip">
          <Users size={16} />
          <span>{user.email}</span>
        </div>
      </aside>

      <section className="fixture-column">
        <header className="column-header">
          <div>
            <p>{currentLeague?.label || "Liga"}</p>
            <h1>Jogos</h1>
          </div>
          <span className="count-pill">{fixtures.length}</span>
        </header>

        {loadingFixtures && <StateLine icon={<Clock size={18} />} text="Carregando jogos..." />}
        {!loadingFixtures && fixtures.length === 0 && <StateLine icon={<Search size={18} />} text="Nenhum jogo encontrado para o filtro." />}
        <div className="fixture-list">
          {fixtures.map((fixture) => (
            <button
              className={`fixture-row ${selectedFixture?.fixture_id === fixture.fixture_id ? "selected" : ""}`}
              key={fixture.fixture_id}
              onClick={() => selectFixture(fixture)}
              type="button"
            >
              <div>
                <strong>
                  {fixture.home_team || "Mandante"} x {fixture.away_team || "Visitante"}
                </strong>
                <span>{formatFixtureMeta(fixture)}</span>
              </div>
              <ChevronRight size={18} />
            </button>
          ))}
        </div>
      </section>

      <section className="detail-column">
        {error && (
          <div className="alert-line">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        {!selectedFixture && !error && (
          <div className="empty-detail">
            <CalendarDays size={32} />
            <p>Selecione um jogo para abrir a analise.</p>
          </div>
        )}

        {selectedFixture && (
          <>
            <header className="detail-header">
              <div>
                <p>{selectedFixture.league || currentLeague?.label}</p>
                <h2>
                  {selectedFixture.home_team || "Mandante"} x {selectedFixture.away_team || "Visitante"}
                </h2>
              </div>
              <span className="status-pill">{selectedFixture.status || "NS"}</span>
            </header>

            <nav className="tabs">
              {tabs.map((tab) => (
                <button className={activeTab === tab ? "active" : ""} key={tab} onClick={() => setActiveTab(tab)} type="button">
                  {tab}
                </button>
              ))}
            </nav>

            {loadingAnalysis && <StateLine icon={<Clock size={18} />} text="Gerando dossie e analise..." />}
            {!loadingAnalysis && analysis && <DetailTab activeTab={activeTab} payload={analysis} />}
          </>
        )}
      </section>
    </main>
  );
}

function DetailTab({ activeTab, payload }: { activeTab: Tab; payload: AnalysisPayload }) {
  if (activeTab === "Analise IA") {
    return <TextBlock text={payload.advisor_text || "Analise indisponivel."} />;
  }
  if (activeTab === "Escalacoes") {
    const lineups = readPath(payload.dossier, ["lineups"]);
    return <JsonBlock data={lineups || { status: "Escalacoes indisponiveis." }} />;
  }
  if (activeTab === "Desfalques") {
    return <TextBlock text={payload.injuries_text || "Desfalques indisponiveis."} />;
  }
  if (activeTab === "Jogadores") {
    return <TextBlock text={payload.player_advice_text || "Jogadores indisponiveis."} />;
  }
  return <JsonBlock data={{ fixture: payload.fixture, data_quality: readPath(payload.dossier, ["data_quality"]), analysis: payload.analysis }} />;
}

function TextBlock({ text }: { text: string }) {
  return <pre className="text-block">{text}</pre>;
}

function JsonBlock({ data }: { data: unknown }) {
  return <pre className="json-block">{JSON.stringify(data, null, 2)}</pre>;
}

function StateLine({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="state-line">
      {icon}
      <span>{text}</span>
    </div>
  );
}

function formatFixtureMeta(fixture: Fixture) {
  const parts = [
    fixture.fixture_date ? new Date(fixture.fixture_date).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : null,
    fixture.round,
    fixture.status
  ]
    .filter(Boolean)
    .join(" - ");
  return parts || "Dados parciais";
}

function readPath(source: Record<string, unknown>, path: string[]) {
  let current: unknown = source;
  for (const key of path) {
    if (!current || typeof current !== "object" || !(key in current)) return null;
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}
