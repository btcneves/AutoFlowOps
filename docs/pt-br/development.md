# Guia de Desenvolvimento

## Pré-requisitos

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose

## Quick Start (Docker)

```bash
make dev
```

Executa `docker compose up --build` e inicia backend, frontend e banco de dados.

- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- Docs da API (Swagger): http://localhost:8000/docs
- Docs da API (ReDoc): http://localhost:8000/redoc

## Setup Local do Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Copie o arquivo de variáveis de ambiente:

```bash
cp ../.env.example ../.env
```

Inicie o servidor de desenvolvimento:

```bash
uvicorn app.main:app --reload
```

Execute os testes:

```bash
PYTHONPATH=. .venv/bin/pytest
```

Execute o lint:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format .
```

## Setup Local do Frontend

```bash
cd frontend
npm install
npm run dev
```

O servidor de desenvolvimento do frontend roda em http://localhost:3000 por padrão.

Execute os testes:

```bash
npm test
```

Execute o lint:

```bash
npm run lint
npm run format
```

Build do frontend para produção:

```bash
npm run build
```

## Dados de Demonstração

Com o Docker em execução, popule um pequeno dataset de demonstração para screenshots ou revisão manual:

```bash
make seed
```

Para desenvolvimento local do backend sem Docker, execute as migrações primeiro e então o seed:

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./autoflowops.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite+aiosqlite:///./autoflowops.db PYTHONPATH=. .venv/bin/python scripts/seed_demo_data.py
```

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste os valores para o seu ambiente.

| Variável | Descrição | Padrão |
|---|---|---|
| `APP_NAME` | Nome da aplicação | `AutoFlowOps` |
| `APP_ENV` | Ambiente (`development`, `production`) | `development` |
| `APP_DEBUG` | Ativa logging verbose de SQL/debug | `false` |
| `APP_SECRET_KEY` | Chave secreta para sessão/autenticação | `change-me` |
| `DATABASE_URL` | String de conexão com o PostgreSQL | Ver `.env.example` |
| `FRONTEND_URL` | URL do frontend para CORS | `http://localhost:3000` |
| `LOG_LEVEL` | Nível de log (`DEBUG`, `INFO`, `WARNING`) | `INFO` |
| `ENABLE_DEMO_MODE` | Ativa dados de demonstração | `true` |

**Nunca commite `.env` no controle de versão.**

## Estrutura do Projeto

```
backend/
├── app/
│   ├── main.py          # App FastAPI, CORS, startup
│   ├── config.py        # Settings (pydantic-settings)
│   ├── api/             # Routers REST
│   ├── models/          # Models SQLAlchemy
│   ├── schemas/         # Schemas Pydantic
│   └── services/        # Agendador, runner e serviços de mascaramento
├── alembic/             # Migrações do banco de dados
├── scripts/             # Scripts utilitários como seed de dados de demonstração
└── tests/
    ├── conftest.py
    └── test_*.py

frontend/
└── src/
    ├── api/             # Cliente HTTP + endpoints tipados
    ├── components/      # Componentes de UI reutilizáveis
    ├── hooks/           # Custom React hooks
    ├── pages/           # Componentes de página no nível de rota
    ├── types/           # Tipos TypeScript
    └── tests/           # Arquivos de teste Vitest
```

## Convenção de Commits

```
feat: adiciona endpoint de criação de job
fix: mascara header de autorização nos logs de execução
docs: atualiza guia de desenvolvimento
test: adiciona testes de execução de job
chore: atualiza docker compose
```
