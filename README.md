# Sports Betting Assistant

Bot de Telegram em Python para atuar como assessor de apostas esportivas. O foco é ajudar o apostador a escolher jogos, interpretar estatísticas, comparar odds e decidir quando faz sentido entrar, reduzir risco ou evitar uma aposta.

O bot não promete lucro e não entrega aposta garantida. Ele organiza dados e gera leitura esportiva com linguagem opinativa, sempre com gestão de risco.

## Funcionalidades atuais

- Menu principal com Futebol, NBA, Minhas Apostas, Configurações e Ajuda.
- Futebol:
  - Jogos de hoje e de amanhã por liga.
  - Jogos com melhor leitura.
  - Análise completa de jogo com melhor aposta, riscos, odds, alternativas, o que evitar e veredito.
  - Jogadores interessantes por jogo quando a API expõe dados suficientes.
- NBA:
  - Jogos de hoje e de amanhã.
  - Props-first: leitura de jogadores por pontos, rebotes, assistências, bolas de 3 e PRA.
- Registro e acompanhamento de apostas.
- Tutorial interativo com `/tutorial`.
- SQLite local por padrão, preparado para PostgreSQL via `DATABASE_URL`.

## Arquitetura

```text
app/
  main.py
  config.py
  bot/              # comandos, menus, callbacks, formatadores e tutorial
  database/         # SQLAlchemy, modelos e repository
  integrations/     # API-Football, balldontlie e The Odds API
  services/         # analysis, advisor engines, odds, futebol, NBA e apostas
  schemas/          # schemas Pydantic
  jobs/             # jobs futuros
```

## Tecnologias

- Python 3.11+
- python-telegram-bot
- SQLAlchemy
- SQLite em desenvolvimento
- PostgreSQL em produção
- python-dotenv
- httpx
- APScheduler preparado para evolução

## Configuração

Crie um `.env` a partir de `.env.example`:

```env
TELEGRAM_BOT_TOKEN=seu-token-do-telegram
DATABASE_URL=sqlite:///./sports_betting_assistant.db
API_FOOTBALL_KEY=sua-chave-api-football
BALLDONTLIE_KEY=sua-chave-balldontlie
ODDS_API_KEY=sua-chave-the-odds-api
BOT_ANALYSIS_STYLE=advisor
```

Importante: nunca versionar `.env`. O projeto já inclui `.gitignore` para proteger chaves, banco local e `venv`.

## Rodando localmente

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app/main.py
```

Se o PowerShell bloquear a ativação:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Como usar no Telegram

1. Envie `/start`.
2. Escolha `Futebol` ou `NBA`.
3. Escolha `Jogos de Hoje`, `Jogos de Amanhã` ou `Jogadores do Dia`.
4. Selecione o jogo.
5. Leia a recomendação principal, riscos, odds, alternativas e veredito.

Comandos úteis:

- `/start`
- `/tutorial`
- `/help`
- `/apostas`
- `/roi`
- `/resultado ID won|lost|void`

## Integrações externas

- API-Football: jogos, times, estatísticas, escalações, jogadores, lesões e previsões quando o plano permitir.
- balldontlie: jogos, times, jogadores e stats da NBA.
- The Odds API: odds pré-jogo e mercados disponíveis.

Quando uma API não expõe dado suficiente, o bot deve responder análise parcial e reduzir confiança, sem inventar estatísticas.

## PostgreSQL

Para migrar de SQLite para PostgreSQL, altere apenas:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/database
```

Para produção, recomenda-se adicionar Alembic antes de evoluir o schema.

## Railway

Arquivos incluídos:

- `Procfile`
- `railway.json`
- `runtime.txt`

Variáveis obrigatórias no Railway:

- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `API_FOOTBALL_KEY`
- `BALLDONTLIE_KEY`
- `ODDS_API_KEY`

Use um serviço PostgreSQL no Railway e configure `DATABASE_URL`.

## Testes e validação

```powershell
python -m compileall app
python -m unittest discover
```

## Roadmap

- MVP atual: assessor por jogo, futebol e NBA, odds e tracking de apostas.
- Próximos passos:
  - Cache com TTL para reduzir rate limit.
  - Alembic para migrations.
  - Testes de callbacks Telegram.
  - Match mais robusto de odds por mercado/linha.
  - Stats avançadas de jogadores e contexto de escalação.
  - Deploy com PostgreSQL e observabilidade.

## Aviso responsável

Este bot é ferramenta de apoio à análise. Ele não garante lucro, não prevê resultado com certeza e não substitui gestão de banca. Apostas envolvem risco.

