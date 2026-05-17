import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  AlertTriangle,
  CalendarDays,
  ChevronRight,
  Clock,
  KeyRound,
  LogOut,
  RefreshCw,
  Search,
  Shield,
  UserPlus,
  Users
} from "lucide-react";
import { api } from "./api";
import { AdminUser, AnalysisPayload, Fixture, FixtureList, League, Tab, User, tabs } from "./types";

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
  const [mode, setMode] = useState<"login" | "reset">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");
    try {
      if (mode === "reset") {
        if (password !== confirmPassword) {
          throw new Error("As senhas nao conferem.");
        }
        await api<User>("/api/auth/reset-password", {
          method: "POST",
          body: JSON.stringify({ email, reset_code: resetCode, password })
        });
        setPassword("");
        setConfirmPassword("");
        setResetCode("");
        setMode("login");
        setMessage("Senha alterada. Entre com a nova senha.");
        return;
      }
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
        <div className="login-tabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")} type="button">
            Entrar
          </button>
          <button className={mode === "reset" ? "active" : ""} onClick={() => setMode("reset")} type="button">
            Alterar senha
          </button>
        </div>
        <label>
          Email
          <input autoFocus value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
        </label>
        {mode === "reset" && (
          <label>
            Chave de recuperacao
            <input value={resetCode} onChange={(event) => setResetCode(event.target.value)} type="password" required />
          </label>
        )}
        <label>
          {mode === "reset" ? "Nova senha" : "Senha"}
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
        </label>
        {mode === "reset" && (
          <label>
            Confirmar nova senha
            <input value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} type="password" required />
          </label>
        )}
        {error && <p className="form-error">{error}</p>}
        {message && <p className="success-line">{message}</p>}
        <button className="primary-button" disabled={loading} type="submit">
          {loading ? "Aguarde..." : mode === "reset" ? "Alterar senha" : "Entrar"}
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
  const [view, setView] = useState<"fixtures" | "users">("fixtures");

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
    <main className={`app-shell ${view === "users" ? "users-mode" : ""}`}>
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
          {user.role === "admin" && (
            <div className="sidebar-actions">
              <button className={view === "fixtures" ? "secondary-button active" : "secondary-button"} onClick={() => setView("fixtures")} type="button">
                <CalendarDays size={16} />
                Jogos
              </button>
              <button className={view === "users" ? "secondary-button active" : "secondary-button"} onClick={() => setView("users")} type="button">
                <Users size={16} />
                Usuarios
              </button>
            </div>
          )}
          {view === "fixtures" && (
          <>
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
          </>
          )}
        </section>

        <div className="user-strip">
          <Users size={16} />
          <span>{user.email}</span>
        </div>
      </aside>

      {view === "fixtures" && (
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
      )}

      <section className="detail-column">
        {view === "users" && user.role === "admin" && <AdminUsersPanel currentUser={user} />}
        {view === "fixtures" && (
        <>
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
        </>
        )}
      </section>
    </main>
  );
}

function AdminUsersPanel({ currentUser }: { currentUser: User }) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwords, setPasswords] = useState<Record<number, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    setLoading(true);
    setError("");
    try {
      setUsers(await api<AdminUser[]>("/api/admin/users"));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Falha ao carregar usuarios.");
    } finally {
      setLoading(false);
    }
  }

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const created = await api<AdminUser>("/api/admin/users", {
        method: "POST",
        body: JSON.stringify({ email, password: newPassword })
      });
      setUsers((items) => [...items, created].sort((a, b) => a.email.localeCompare(b.email)));
      setEmail("");
      setNewPassword("");
      setMessage(`Usuario ${created.email} criado.`);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Falha ao criar usuario.");
    }
  }

  async function changePassword(target: AdminUser) {
    const password = passwords[target.id] || "";
    setMessage("");
    setError("");
    try {
      const updated = await api<AdminUser>(`/api/admin/users/${target.id}/password`, {
        method: "PUT",
        body: JSON.stringify({ password })
      });
      setUsers((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setPasswords((items) => ({ ...items, [target.id]: "" }));
      setMessage(`Senha alterada para ${updated.email}.`);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Falha ao alterar senha.");
    }
  }

  return (
    <div className="admin-panel">
      <header className="detail-header">
        <div>
          <p>Administracao</p>
          <h2>Usuarios</h2>
        </div>
        <span className="status-pill">{users.length}</span>
      </header>

      <div className="admin-content">
        {error && (
          <div className="alert-line compact">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}
        {message && <p className="success-line">{message}</p>}

        <form className="admin-form" onSubmit={createUser}>
          <h3>Novo usuario</h3>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
          </label>
          <label>
            Senha inicial
            <input value={newPassword} onChange={(event) => setNewPassword(event.target.value)} type="password" minLength={8} required />
          </label>
          <button className="primary-button" type="submit">
            <UserPlus size={16} />
            Criar usuario
          </button>
        </form>

        <section className="users-table">
          <div className="users-table-head">
            <span>Email</span>
            <span>Perfil</span>
            <span>Nova senha</span>
          </div>
          {loading && <StateLine icon={<Clock size={18} />} text="Carregando usuarios..." />}
          {!loading &&
            users.map((item) => (
              <div className="user-row" key={item.id}>
                <div>
                  <strong>{item.email}</strong>
                  {item.id === currentUser.id && <span>voce</span>}
                </div>
                <span className="role-pill">{item.role}</span>
                <div className="password-action">
                  <input
                    aria-label={`Nova senha para ${item.email}`}
                    minLength={8}
                    type="password"
                    value={passwords[item.id] || ""}
                    onChange={(event) => setPasswords((values) => ({ ...values, [item.id]: event.target.value }))}
                  />
                  <button className="icon-button bordered" disabled={(passwords[item.id] || "").length < 8} onClick={() => changePassword(item)} title="Alterar senha" type="button">
                    <KeyRound size={17} />
                  </button>
                </div>
              </div>
            ))}
        </section>
      </div>
    </div>
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
