# Assist Bet Dashboard

Dashboard web em Python + React para analisar jogos de futebol com apoio de IA. O foco e explicar roteiro provavel, matchups, contexto competitivo, riscos, escalacoes, desfalques e ideias qualitativas de mercado.

O produto nao promete lucro, nao trabalha com aposta garantida e nao depende de odds para decidir. Ele organiza dados da API-Football e usa OpenAI para transformar o dossie em leitura esportiva util.

## Funcionalidades

- Login web com cookie HTTP-only.
- Rate limit em tentativas de login.
- Lista de jogos por liga e data.
- Detalhe clicavel por partida.
- Abas de analise da IA, escalacoes, desfalques, jogadores e dados brutos.
- Fallback local quando a OpenAI nao esta configurada ou retorna JSON invalido.
- Cache TTL para reduzir chamadas repetidas a APIs externas.
- Docs do FastAPI desabilitadas em producao.

## Arquitetura

```text
app/
  main.py
  config.py
  web/              # FastAPI, auth, APIs do dashboard e CLI de usuario
  database/         # SQLAlchemy, modelos e repository
  integrations/     # API-Football e OpenAI
  services/         # analise de futebol, contexto, dossie, jogadores e IA
  schemas/          # schemas Pydantic
frontend/           # React + Vite + TypeScript
migrations/         # Alembic
```

## Configuracao

Crie um `.env` a partir de `.env.example`:

```env
ENVIRONMENT=development
DATABASE_CREATE_ALL=false
DATABASE_MIGRATE_ON_STARTUP=false
WEB_SECRET_KEY=troque-em-producao-32-bytes-minimo
WEB_SESSION_COOKIE_NAME=assist_bet_session
WEB_SESSION_EXPIRE_MINUTES=10080
LOGIN_RATE_LIMIT_ATTEMPTS=5
LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
FIXTURE_PAYLOAD_CACHE_SECONDS=300

DATABASE_URL=sqlite:///./sports_betting_assistant.db
OPENAI_API_KEY=sua-chave-openai
OPENAI_MODEL=gpt-4o-mini

API_FOOTBALL_KEY=sua-chave-api-football
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
API_FOOTBALL_HOST=
```

Em producao, `WEB_SECRET_KEY` e obrigatoria e deve ter pelo menos 32 caracteres.

## Rodando Localmente

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.web.create_user --email admin@example.com
cd frontend
npm install
npm run build
cd ..
uvicorn app.web.main:app --reload
```

Abra `http://127.0.0.1:8000` e entre com o usuario criado. A CLI de usuario pede a senha via prompt para evitar expor credenciais no historico do terminal.

Para desenvolver o frontend com hot reload:

```powershell
cd frontend
npm install
npm run dev
```

O Vite encaminha `/api` para `http://127.0.0.1:8000`.

## PostgreSQL

Para migrar de SQLite para PostgreSQL:

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

O deploy usa Nixpacks como fonte unica de build:

- `railway.json` seleciona o builder e o comando de start.
- `nixpacks.toml` instala Python/Node, roda `pip install`, `npm install`, `npm run build` e valida `frontend/dist/index.html`.

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

O unico usuario admin permitido e `rafaelmslima.miranda2@gmail.com`. Crie usuarios comuns com:

```powershell
python -m app.web.user_admin create --email usuario@example.com
```

Troque a senha de um usuario existente com:

```powershell
python -m app.web.user_admin password --email rafaelmslima.miranda2@gmail.com
```

## Testes E Validacao

```powershell
python -m compileall app
python -m pytest
cd frontend
npm run build
```

## Migracao Irreversivel

`0003_remove_telegram_legacy.py` remove tabelas antigas do Telegram e e irreversivel por design. Para rollback desse ponto, restaure backup anterior a migration.

## Aviso Responsavel

Este produto e ferramenta de apoio a analise. Ele nao garante lucro, nao preve resultado com certeza e nao substitui gestao de risco. Apostas envolvem risco.
