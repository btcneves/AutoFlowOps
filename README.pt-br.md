# AutoFlowOps

**Plataforma de automação open-source para jobs HTTP agendados, integrações de API, webhooks, alertas, notificações externas e relatórios operacionais.**

O AutoFlowOps ajuda desenvolvedores e times pequenos a substituir processos manuais frágeis por fluxos de automação confiáveis, observáveis e documentados — self-hosted, reproduzíveis e totalmente open source.

[![Backend CI](https://github.com/btcneves/autoflowops/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/btcneves/autoflowops/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/btcneves/autoflowops/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/btcneves/autoflowops/actions/workflows/frontend-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> [English version](README.md)

---

## O Problema

Times e desenvolvedores frequentemente têm rotinas espalhadas em scripts isolados, planilhas, automações improvisadas e ferramentas pagas sem visibilidade:

- Polling periódico de APIs sem histórico de execução
- Webhooks recebidos sem trilha de auditoria
- Cron jobs que falham silenciosamente
- Tarefas manuais repetitivas sem rastreabilidade
- Integrações que quebram sem alertas

## A Solução

O AutoFlowOps centraliza essas rotinas em uma única plataforma self-hosted:

- **Jobs** — crie, edite e agende jobs HTTP pela interface ou API; execute manualmente ou por agendamento em intervalos/cron
- **Execuções** — histórico persistente com status, tempos, prévia de respostas e segredos mascarados
- **Webhooks** — receba eventos externos, armazene payloads com validação por token, reprocesse eventos
- **Alertas** — alertas automáticos em falhas de jobs e webhooks, com fluxos de reconhecimento e resolução
- **Regras condicionais de alerta** — dispare alertas por status HTTP, duração, texto da resposta ou limites de falhas consecutivas
- **Notificações** — envie alertas críticos para Discord, Telegram, SMTP e webhooks customizados
- **Políticas de escalonamento** — escalonamento em múltiplos passos com delays configuráveis por etapa
- **Permissões** — roles admin, operator e viewer aplicados server-side; trilha de auditoria de todas as ações sensíveis
- **Relatórios** — exporte o histórico operacional como JSON, Markdown ou CSV
- **Dashboard** — métricas em tempo real: jobs ativos, execuções, taxa de falhas e gráfico de 7 dias

---

## Funcionalidades

- Self-hosted, roda em qualquer servidor ou ambiente Docker
- Backend REST API (FastAPI + PostgreSQL), worker Celery e frontend React
- Jobs agendados com intervalo (segundos) e expressões cron
- Fila de jobs com Redis para execuções manuais e agendadas
- Executor HTTP com timeout configurável
- Receptor de webhooks com validação por token secreto (SHA-256)
- Histórico de execuções com segredos mascarados e prévia de respostas
- Sistema interno de alertas para execuções com falha
- Regras condicionais de alerta por job para limites operacionais customizados
- Canais de notificação externos para alertas críticos (Discord, Telegram, SMTP, webhooks customizados)
- Templates de notificação e políticas de escalonamento em múltiplos passos
- Controle de acesso por roles (admin / operator / viewer) aplicado server-side
- Log de auditoria de todas as operações sensíveis com ator, recurso e metadados mascarados
- API e frontend de gerenciamento de usuários (somente admin)
- Relatórios operacionais exportáveis como JSON, Markdown ou CSV
- Stream de eventos em tempo real via WebSocket — atualizações ao vivo sem refresh de página
- Inicialização em um comando via Docker Compose — build local ou imagens versionadas do GHCR
- GitHub Actions CI para backend e frontend; publicação automática de imagem Docker a cada tag de release
- Open-source sob licença MIT

---

## Stack

| Camada | Tecnologia |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic |
| Banco de dados | PostgreSQL 16 |
| Agendador | APScheduler despachando para Celery |
| Fila / Worker | Redis + Celery |
| Cliente HTTP | httpx |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Estado/Fetch | TanStack Query v5 |
| Gráficos | Recharts |
| Testes | pytest (backend), Vitest + Testing Library (frontend) |
| Lint | ruff (backend), ESLint + Prettier (frontend) |
| DevOps | Docker, Docker Compose, GitHub Actions, GHCR, Makefile |

---

## Visão Geral da Arquitetura

```text
Browser
  └─> Frontend React/Vite (porta 3000)
        └─> Backend FastAPI REST API (porta 8000)
              ├─> SQLAlchemy async session
              │     └─> PostgreSQL (porta 5432)
              ├─> APScheduler (in-process)
              │     └─> Fila Redis
              │           └─> Worker Celery (executa jobs, cria execuções + alertas)
              ├─> Receptor de webhooks (valida token, armazena eventos)
              └─> Canais de notificação (Discord, SMTP, webhooks customizados)
```

Para uma descrição detalhada de cada componente e fluxo de dados, veja [docs/pt-br/architecture.md](docs/pt-br/architecture.md).

---

## Quick Start

### Opção A — Baixar do registry (sem build)

A forma mais rápida de rodar o AutoFlowOps é baixar as imagens pré-compiladas do GitHub Container Registry:

```bash
git clone https://github.com/btcneves/autoflowops.git
cd autoflowops
bash scripts/setup.sh
```

O script solicita a tag da imagem (padrão `latest`), copia `.env.example` para `.env`, baixa as imagens e inicia o stack. Edite `.env` e altere `APP_SECRET_KEY` e `JWT_SECRET_KEY` antes de qualquer uso em produção.

Para rodar uma versão específica:

```bash
IMAGE_TAG=v1.2.0 bash scripts/setup.sh
# ou
IMAGE_TAG=v1.2.0 make registry-up
```

### Opção B — Build a partir do código-fonte

### Requisitos

- Docker + Docker Compose

### 1. Clonar e configurar

```bash
git clone https://github.com/btcneves/autoflowops.git
cd autoflowops
cp .env.example .env
```

Edite `.env` e altere `APP_SECRET_KEY` e `JWT_SECRET_KEY` antes de fazer deploy em produção.

### 2. Iniciar

```bash
make dev
# ou
docker compose up --build
```

| Serviço | URL |
| --- | --- |
| Frontend | <http://localhost:3000> |
| Backend API | <http://localhost:8000> |
| Docs da API (Swagger) | <http://localhost:8000/docs> |
| Docs da API (ReDoc) | <http://localhost:8000/redoc> |
| Redis | `localhost:6379` |

### 3. Verificar

```bash
curl http://localhost:8000/api/health
```

Esperado:

```json
{"status": "ok", "app": "AutoFlowOps", "env": "development", "database": "ok"}
```

### 4. Dados de demonstração (opcional)

```bash
make seed
```

Cria um conjunto de jobs, execuções, webhooks e alertas de demonstração para que o dashboard renderize com dados imediatamente.

---

## Desenvolvimento Local (sem Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Veja [docs/pt-br/development.md](docs/pt-br/development.md) para o guia completo de desenvolvimento local, incluindo variáveis de ambiente e configuração do banco de dados.

---

## Testes

```bash
# Backend
cd backend
PYTHONPATH=. pytest

# Frontend
cd frontend
npm test

# Ambos (via Makefile)
make test
```

**Status atual dos testes:**

| Suite | Testes | Status |
| --- | --- | --- |
| Backend | 260 | Passando |
| Frontend | 76 | Passando |

---

## Lint e Formatação

```bash
# Backend
cd backend
ruff check .
ruff format .

# Frontend
cd frontend
npm run lint
npm run format

# Ambos (via Makefile)
make lint
make format
```

---

## Targets do Makefile

```bash
make dev           # docker compose up --build (foreground)
make up            # docker compose up -d --build (background)
make down          # docker compose down
make logs          # docker compose logs -f
make worker-logs   # docker compose logs -f worker
make test          # executa testes de backend + frontend
make lint          # executa lint de backend + frontend
make format        # executa formatação de backend + frontend
make seed          # carrega dados de demonstração nos containers Docker em execução
make prod-up       # inicia o stack de produção com proxy reverso Caddy
make prod-down
make prod-logs
make prod-validate
make setup         # copia .env.example para .env
make pull          # baixa imagens de backend + frontend do GHCR (IMAGE_TAG=latest)
make registry-up   # inicia o stack usando imagens do GHCR (IMAGE_TAG=latest)
make registry-down # para o stack baseado no registry
make registry-logs # transmite logs do stack baseado no registry
```

---

## Estrutura do Projeto

```text
autoflowops/
├── backend/         Aplicação FastAPI, models, services, testes
├── frontend/        Aplicação React, components, pages, testes
├── docs/            Documentação
├── examples/        Exemplos de uso (receitas curl)
├── scripts/         Scripts utilitários
├── .github/         Workflows CI e templates de PR/issue
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Documentação

| Documento | Descrição |
| --- | --- |
| [Arquitetura](docs/pt-br/architecture.md) | Componentes, modelo de dados, agendamento e modelo de segurança |
| [Guia de Desenvolvimento](docs/pt-br/development.md) | Setup local, variáveis de ambiente, estrutura do projeto |
| [Segurança](docs/pt-br/security.md) | Política de mascaramento, tokens de webhook, boas práticas de .env |
| [Roadmap](docs/pt-br/roadmap.md) | Funcionalidades concluídas, próximos passos e planos futuros |
| [Deploy](docs/pt-br/deployment.md) | Docker Compose, migrações e checklist de produção |

---

## Roadmap

| Funcionalidade | Status |
| --- | --- |
| Backend FastAPI + REST API | ✅ Concluído |
| PostgreSQL + SQLAlchemy + Alembic | ✅ Concluído |
| Executor HTTP com mascaramento de segredos | ✅ Concluído |
| APScheduler (intervalo + cron) | ✅ Concluído |
| Dashboard com métricas reais + gráfico | ✅ Concluído |
| Webhook CRUD + validação por token + eventos | ✅ Concluído |
| Alertas internos + reconhecimento/resolução | ✅ Concluído |
| Relatórios (JSON, Markdown, CSV) | ✅ Concluído |
| Docker Compose + GitHub Actions CI | ✅ Concluído |
| Interface de gerenciamento de jobs | ✅ Concluído |
| Interface de histórico de execuções | ✅ Concluído |
| Autenticação (JWT) | ✅ Concluído |
| Proteção SSRF para jobs HTTP | ✅ Concluído |
| Rate limiting de webhooks | ✅ Concluído |
| Guia de deploy em VPS | ✅ Concluído |
| Proxy reverso Caddy + Compose de produção | ✅ Concluído |
| Health checks de produção e CI de configuração | ✅ Concluído |
| Worker Celery + Redis | ✅ Concluído |
| Execução de jobs manuais e agendados via fila | ✅ Concluído |
| Notificações externas (Discord, Telegram, email) | ✅ Concluído |
| Templates de notificação + políticas de escalonamento | ✅ Concluído |
| RBAC (controle de acesso por roles) | ✅ Concluído |
| Log de auditoria com ator e metadados mascarados | ✅ Concluído |
| API e interface de gerenciamento de usuários | ✅ Concluído |
| Stream de eventos em tempo real via WebSocket | ✅ Concluído |
| Registry de imagens Docker (GHCR) + script de setup | ✅ Concluído |
| Interface avançada de política de retry | ✅ Concluído |

Veja [docs/pt-br/roadmap.md](docs/pt-br/roadmap.md) para o roadmap completo.

---

## Segurança

- Segredos são mascarados em todos os logs e registros de execução armazenados
- Tokens de webhook são armazenados como hashes SHA-256, nunca em texto simples
- `.env` nunca é versionado; apenas `.env.example` é commitado
- Autenticação JWT obrigatória; credenciais do admin inicial definidas via variáveis `ADMIN_EMAIL` / `ADMIN_PASSWORD` — altere antes de fazer deploy
- Controle de acesso por roles (admin / operator / viewer) aplicado em todos os endpoints de escrita
- Log de auditoria registra todas as operações sensíveis atomicamente com ator, endereço IP e metadados mascarados
- Proteção SSRF bloqueia URLs de jobs direcionadas a faixas privadas/internas por padrão
- Credenciais de canais de notificação criptografadas em repouso (Fernet AES)

Veja [SECURITY.md](SECURITY.md) para a política de divulgação de vulnerabilidades e regras completas de mascaramento.

---

## Contribuição

Contribuições são bem-vindas. Leia [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir um pull request.

Para vulnerabilidades de segurança, siga [SECURITY.md](SECURITY.md) — não abra issues públicas.

---

## Licença

[MIT](LICENSE) © 2026 AutoFlowOps Contributors
