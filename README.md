# Football Match Analyst Dashboard

Dashboard web e bot de Telegram em Python para analisar jogos de futebol com apoio de IA. O foco e explicar como a partida tende a acontecer: roteiro provavel, matchups, contexto competitivo, riscos e ideias qualitativas de mercados.

O produto nao promete lucro, nao trabalha com aposta garantida e nao depende de odds para decidir. Ele organiza dados da API-Football e usa OpenAI para transformar o dossie em leitura esportiva util.

## Funcionalidades atuais

- Dashboard web com login, lista de jogos por liga/data e detalhes por partida.
- Tela de detalhes com analise da IA, escalacoes, desfalques, jogadores e dados brutos.
- Bot de Telegram mantido como canal opcional:
  - Jogos de hoje e de amanha por liga.
  - Melhores leituras do dia por clareza do roteiro e qualidade dos dados.
  - Analise inteligente por jogo com ideia geral, roteiro, matchups, riscos, ideias de apostas e confianca.
  - Jogadores e desfalques quando a API expoe dados suficientes.
- Busca por confronto digitado no formato `Time A x Time B`.
- SQLite local por padrao, preparado para PostgreSQL via `DATABASE_URL`.

## Arquitetura

```text
app/
  main.py
  config.py
  web/              # FastAPI, auth, APIs do dashboard e CLI de usuario
  bot/              # comandos, menus, callbacks, formatadores e tutorial
  database/         # SQLAlchemy, modelos e repository legado
  integrations/     # API-Football e OpenAI
  services/         # analise de futebol, contexto, dossie e IA
  schemas/          # schemas Pydantic
  jobs/             # jobs futuros/legados
frontend/           # React + Vite + TypeScript
```

## Tecnologias

- Python 3.11+
- FastAPI
- React + Vite
- python-telegram-bot
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
TELEGRAM_BOT_TOKEN=seu-token-do-telegram
DATABASE_URL=sqlite:///./sports_betting_assistant.db
OPENAI_API_KEY=sua-chave-openai
OPENAI_MODEL=gpt-4o-mini
API_FOOTBALL_KEY=sua-chave-api-football
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
API_FOOTBALL_HOST=
BOT_ANALYSIS_STYLE=advisor
WEB_SECRET_KEY=troque-em-producao-32-bytes-minimo
WEB_SESSION_COOKIE_NAME=assist_bet_session
WEB_SESSION_EXPIRE_MINUTES=10080
```

Importante: nunca versionar `.env`. O projeto ja inclui `.gitignore` para proteger chaves, banco local, build do frontend e ambientes virtuais.

## Rodando o dashboard localmente

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

## Rodando o bot Telegram

```powershell
python app/main.py
```

Comandos uteis no Telegram:

- `/start`
- `/tutorial`
- `/help`
- `/status`

## Integracoes externas

- API-Football: jogos, times, estatisticas, classificacao, calendario, escalacoes, jogadores, lesoes e previsoes quando o plano permitir.
- OpenAI: interpreta o dossie de futebol e gera a leitura inteligente do jogo.

Quando uma API nao expoe dado suficiente, o app deve responder analise parcial e reduzir confianca, sem inventar estatisticas.

## PostgreSQL

Para migrar de SQLite para PostgreSQL, altere apenas:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/database
```

Se o provedor entregar `postgresql://...` ou `postgres://...`, o app converte automaticamente para o driver `psycopg` usado no `requirements.txt`.

O projeto inclui migrations com Alembic. Antes de subir em producao, rode:

```powershell
alembic upgrade head
```

Em producao (`ENVIRONMENT=production`), o app tambem executa `alembic upgrade head` na inicializacao por padrao. Para desativar, defina `DATABASE_MIGRATE_ON_STARTUP=false` e rode a migration por fora.

## Railway

Arquivos incluidos:

- `Procfile`
- `railway.json`
- `nixpacks.toml`
- `runtime.txt`

Variaveis obrigatorias no Railway para o dashboard:

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

Para manter o Telegram em paralelo, crie um segundo servico/worker usando:

```powershell
python app/main.py
```

Nesse worker, `TELEGRAM_BOT_TOKEN` tambem e obrigatorio.

## Testes e validacao

```powershell
python -m compileall app
python -m pytest
cd frontend
npm run build
```

## Roadmap

- Aprimorar ranking de melhores leituras por clareza de roteiro.
- Salvar analises geradas e comparar com o pos-jogo para auditar acertos e erros.
- Melhorar leitura de escalacoes confirmadas e impacto de desfalques.
- Adicionar observabilidade de falhas de API e qualidade de dados.

## Aviso responsavel

Este produto e ferramenta de apoio a analise. Ele nao garante lucro, nao preve resultado com certeza e nao substitui gestao de risco. Apostas envolvem risco.
