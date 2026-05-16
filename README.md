# Assist Bet Dashboard

Dashboard web em Python + React para analisar jogos de futebol com apoio de IA. O foco e explicar como a partida tende a acontecer: roteiro provavel, matchups, contexto competitivo, riscos, escalações, desfalques e ideias qualitativas de mercados.

O produto nao promete lucro, nao trabalha com aposta garantida e nao depende de odds para decidir. Ele organiza dados da API-Football e usa OpenAI para transformar o dossie em leitura esportiva util.

## Funcionalidades

- Login web com usuarios em banco PostgreSQL/SQLite.
- Lista de jogos por liga e data.
- Detalhe clicavel por partida.
- Abas de analise da IA, escalações, desfalques, jogadores e dados brutos.
- Fallback local quando a OpenAI nao esta configurada ou retorna JSON invalido.
- Cache TTL para reduzir chamadas repetidas a APIs externas.

## Arquitetura

```text
app/
  main.py
  config.py
  web/              # FastAPI, auth, APIs do dashboard e CLI de usuario
  database/         # SQLAlchemy, modelos e repository
  integrations/     # API-Football e OpenAI
  services/         # analise de futebol, contexto, dossie e IA
  schemas/          # schemas Pydantic
  jobs/             # jobs futuros/legados sem interface ativa
frontend/           # React + Vite + TypeScript
```

## Tecnologias

- Python 3.11+
- FastAPI
- React + Vite
- SQLAlchemy
- SQLite em desenvolvimento
- PostgreSQL em producao
- python-dotenv
- httpx
- Pydantic
- Alembic

## Configuracao

Crie um `.env` a partir de `.env.example`:

```env
ENVIRONMENT=development
DATABASE_CREATE_ALL=false
DATABASE_MIGRATE_ON_STARTUP=false
BOT_ANALYSIS_STYLE=advisor
WEB_SECRET_KEY=troque-em-producao-32-bytes-minimo
WEB_SESSION_COOKIE_NAME=assist_bet_session
WEB_SESSION_EXPIRE_MINUTES=10080

DATABASE_URL=sqlite:///./sports_betting_assistant.db
OPENAI_API_KEY=sua-chave-openai
OPENAI_MODEL=gpt-4o-mini

API_FOOTBALL_KEY=sua-chave-api-football
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
API_FOOTBALL_HOST=
```

## Rodando localmente

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.web.create_user --email admin@example.com --password "troque-esta-senha"
cd frontend
npm install
npm run build
cd ..
uvicorn app.web.main:app --reload
```

Abra `http://127.0.0.1:8000` e entre com o usuario criado.

Para desenvolver o frontend com hot reload:

```powershell
cd frontend
npm install
npm run dev
```

O Vite encaminha `/api` para `http://127.0.0.1:8000`.

## PostgreSQL

Para migrar de SQLite para PostgreSQL, altere:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/database
```

Se o provedor entregar `postgresql://...` ou `postgres://...`, o app converte automaticamente para o driver `psycopg`.

Antes de subir em producao, rode:

```powershell
alembic upgrade head
```

Em producao (`ENVIRONMENT=production`), o app executa migrations na inicializacao quando `DATABASE_MIGRATE_ON_STARTUP=true`.

## Railway

Arquivos incluidos:

- `Procfile`
- `railway.json`
- `nixpacks.toml`
- `runtime.txt`

Variaveis obrigatorias:

- `DATABASE_URL`
- `ENVIRONMENT=production`
- `DATABASE_MIGRATE_ON_STARTUP=true`
- `OPENAI_API_KEY`
- `OPENAI_MODEL=gpt-4o-mini`
- `API_FOOTBALL_KEY`
- `WEB_SECRET_KEY`

O processo web sobe com:

```powershell
uvicorn app.web.main:app --host 0.0.0.0 --port $PORT
```

Crie o primeiro usuario com:

```powershell
python -m app.web.create_user --email admin@example.com --password "sua-senha-forte"
```

## Testes e validacao

```powershell
python -m compileall app
python -m pytest
cd frontend
npm run build
```

## Aviso responsavel

Este produto e ferramenta de apoio a analise. Ele nao garante lucro, nao preve resultado com certeza e nao substitui gestao de risco. Apostas envolvem risco.
