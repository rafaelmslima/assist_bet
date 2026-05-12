# Football Match Analyst Bot

Bot de Telegram em Python para analisar jogos de futebol com apoio de IA. O foco agora e explicar como a partida tende a acontecer: roteiro provavel, matchups, contexto competitivo, riscos e ideias qualitativas de mercados.

O bot nao promete lucro, nao trabalha com aposta garantida e nao depende de odds para decidir. Ele organiza dados da API-Football e usa OpenAI para transformar o dossie em leitura esportiva util.

## Funcionalidades atuais

- Menu principal com Futebol, Status e Ajuda.
- Futebol:
  - Jogos de hoje e de amanha por liga.
  - Melhores leituras do dia por clareza do roteiro e qualidade dos dados.
  - Analise inteligente por jogo com ideia geral, roteiro, matchups, riscos, ideias de apostas e confianca.
  - Jogadores e desfalques quando a API expõe dados suficientes.
- Busca por confronto digitado no formato `Time A x Time B`.
- SQLite local por padrao, preparado para PostgreSQL via `DATABASE_URL`.

## Arquitetura

```text
app/
  main.py
  config.py
  bot/              # comandos, menus, callbacks, formatadores e tutorial
  database/         # SQLAlchemy, modelos e repository legado
  integrations/     # API-Football e OpenAI
  services/         # analise de futebol, contexto, dossie e IA
  schemas/          # schemas Pydantic
  jobs/             # jobs futuros/legados
```

## Tecnologias

- Python 3.11+
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
```

Importante: nunca versionar `.env`. O projeto ja inclui `.gitignore` para proteger chaves, banco local e ambientes virtuais.

## Rodando localmente

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app/main.py
```

Se o PowerShell bloquear a ativacao:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Como usar no Telegram

1. Envie `/start`.
2. Escolha `Futebol`.
3. Escolha `Jogos de Hoje`, `Jogos de Amanha`, `Melhores Leituras` ou `Buscar Jogo`.
4. Selecione o jogo.
5. Leia o roteiro da partida, os pontos-chave, as ideias qualitativas e a confianca da leitura.

Comandos uteis:

- `/start`
- `/tutorial`
- `/help`
- `/status`

## Integracoes externas

- API-Football: jogos, times, estatisticas, classificacao, calendario, escalações, jogadores, lesoes e previsoes quando o plano permitir.
- OpenAI: interpreta o dossie de futebol e gera a leitura inteligente do jogo.

Quando uma API nao expõe dado suficiente, o bot deve responder analise parcial e reduzir confianca, sem inventar estatisticas.

## PostgreSQL

Para migrar de SQLite para PostgreSQL, altere apenas:

```env
DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/database
```

Se o provedor entregar `postgresql://...` ou `postgres://...`, o app converte automaticamente para o driver `psycopg` usado no `requirements.txt`.

O projeto inclui migrations com Alembic. Antes de subir o bot em producao, rode:

```powershell
alembic upgrade head
```

Em producao (`ENVIRONMENT=production`), o app tambem executa `alembic upgrade head` na inicializacao por padrao. Para desativar, defina `DATABASE_MIGRATE_ON_STARTUP=false` e rode a migration por fora.

## Railway

Arquivos incluidos:

- `Procfile`
- `railway.json`
- `runtime.txt`

Variaveis obrigatorias no Railway:

- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`
- `ENVIRONMENT=production`
- `OPENAI_API_KEY`
- `OPENAI_MODEL=gpt-4o-mini`
- `API_FOOTBALL_KEY`

Use um servico PostgreSQL no Railway, configure `DATABASE_URL` e execute `alembic upgrade head` antes de iniciar o worker.

## Testes e validacao

```powershell
python -m compileall app
python -m pytest
```

## Roadmap

- Aprimorar ranking de melhores leituras por clareza de roteiro.
- Salvar analises geradas e comparar com o pos-jogo para auditar acertos e erros.
- Melhorar leitura de escalações confirmadas e impacto de desfalques.
- Adicionar observabilidade de falhas de API e qualidade de dados.

## Aviso responsavel

Este bot e ferramenta de apoio a analise. Ele nao garante lucro, nao preve resultado com certeza e nao substitui gestao de risco. Apostas envolvem risco.
