export type User = { id: number; email: string; role: string };

export type League = { key: string; label: string; league_id: number; season: number };

export type Fixture = {
  fixture_id: string | number;
  league?: string | null;
  round?: string | null;
  fixture_date?: string | null;
  status?: string | null;
  home_team?: string | null;
  away_team?: string | null;
};

export type FixtureList = {
  ok: boolean;
  date: string;
  league: League | null;
  fixtures: Fixture[];
  error?: string | null;
};

export type AnalysisPayload = {
  fixture: Record<string, unknown>;
  advisor_text: string;
  analysis_mode: string;
  analysis: Record<string, unknown>;
  advice: Record<string, unknown>;
  dossier: Record<string, unknown>;
  card_text: string;
  player_advice_text: string;
  injuries_text: string;
};

export const tabs = ["Analise IA", "Escalacoes", "Desfalques", "Jogadores", "Dados"] as const;
export type Tab = (typeof tabs)[number];
