# Roadmap

Este documento acompanha o status das funcionalidades do AutoFlowOps entre as fases concluídas, planejadas e futuras.

---

## Concluído (v1.0.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **Release self-hosted estável** | Consolida o conjunto completo de funcionalidades do AutoFlowOps na primeira release major: jobs, execuções, webhooks, alertas, relatórios, notificações, RBAC, log de auditoria, eventos em tempo real, fila de worker, Docker Compose e distribuição via GHCR |
| **Alinhamento de versão** | Metadados do pacote backend, `/api/version`, metadados do pacote frontend e lockfile reportam `1.0.0` |
| **Empacotamento da release** | Notas de release v1.0.0 dedicadas, exemplos de setup fixados em `v1.0.0` e workflow de publicação Docker produzindo tags de imagem `vX.Y.Z` e semver |
| **Interface avançada de política de retry** | Formulário de job expõe contagem de retry (0–10) e delay de retry; página de detalhe do job mostra cards de configuração de retry e badge de tentativa por execução; tabela e página de detalhe de execução exibem `retry_attempt` |

---

## Concluído (v0.9.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **Registry de imagens Docker** | Imagens de backend e frontend publicadas no GHCR a cada tag de versão; labels OCI, cache de build via cache do GitHub Actions; tags: `vX.Y.Z`, `X.Y`, `latest` |
| **Dockerfiles melhorados** | Backend: adicionado `curl`, instrução `HEALTHCHECK`, labels OCI, usuário não-root criado cedo, camada de cache de dependências isolada; `.dockerignore` estendido para excluir testes, eggs, arquivos SQLite |
| **Dockerfile do Frontend** | Labels OCI adicionados; `.dockerignore` estendido para excluir `src/tests/` e `coverage/` |
| **`docker-compose.registry.yml`** | Arquivo compose alternativo que usa imagens `ghcr.io/btcneves/autoflowops-backend` e `ghcr.io/btcneves/autoflowops-frontend`; variável de ambiente `IMAGE_TAG` seleciona a versão |
| **`scripts/setup.sh`** | Script de setup interativo (ou não-interativo via `IMAGE_TAG`): verifica pré-requisitos, copia `.env.example`, baixa imagens do GHCR, inicia o stack, aguarda endpoints de health e imprime URLs dos serviços |
| **Targets do Makefile** | `pull` — baixa imagens do GHCR; `registry-up` — inicia com imagens GHCR; `registry-down` — para; `registry-logs` — transmite logs; variável `IMAGE_TAG` controla a versão |
| **Workflow `docker-publish.yml`** | Workflow GitHub Actions acionado em push de tag `v*.*.*`; compila e publica imagens de backend e frontend no GHCR; usa cache de build (`type=gha`) para rebuilds rápidos; jobs separados para cada serviço |

---

## Concluído (v0.8.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **Endpoint WebSocket** | `GET /ws/events?token=<JWT>` — faz upgrade para conexão persistente; JWT validado contra banco em cada conexão; conexões rejeitadas recebem código 1008 |
| **ConnectionManager** | Registry in-process de conexões WebSocket ativas; conexões mortas removidas no próximo broadcast |
| **Fan-out Redis Pub/Sub** | Task asyncio subscriber única por processo backend; encaminha mensagens do canal `autoflowops:events` para todos os clientes conectados; falha graciosamente quando Redis não está disponível |
| **Serviço `event_publisher`** | `publish_event()` (sync, Celery) e `publish_event_async()` (async, FastAPI); ignora erros de publicação para nunca bloquear o caminho de execução primário |
| **Evento `execution.started`** | Publicado pelo `http_runner` quando uma execução transiciona para `running` |
| **Evento `execution.completed`** | Publicado pelo `http_runner` e pelo worker Celery em todo estado terminal, incluindo `retrying` |
| **Evento `alert.created`** | Publicado quando uma falha de job cria um alerta, tanto pelo APScheduler quanto pelo Celery |
| **Hook `useWebSocket`** | Reconexão com backoff exponencial (máx 30s); para de reconectar no código 1008; fecha ao desmontar; sem reconexão quando o token de acesso está ausente |
| **Componente `LiveIndicator`** | Ponto verde pulsante quando conectado; ponto cinza quando conectando; invisível quando fechado ou com falha de autenticação (fallback de polling ainda ativo) |
| **Página de Execuções em tempo real** | Invalida cache de query em `execution.started` / `execution.completed`; exibe `LiveIndicator` |
| **Página de Jobs em tempo real** | Invalida cache de jobs em `execution.completed` (atualiza `last_run_at`); exibe `LiveIndicator` |
| **Página de Alertas em tempo real** | Invalida cache de alertas em `alert.created`; exibe `LiveIndicator` |
| **Testes de WS no backend** | 7 testes: sem token, token inválido, token de usuário fantasma, admin válido, ping/pong, broadcast, limpeza de conexão morta |
| **Testes de WS no frontend** | 10 testes em `useWebSocket.test.ts`: conexão, status inicial, auth_error (sem token), open, lastEvent, filtragem pong/connected, sem reconexão no código 1008, reconexão em fechamento normal, fechamento ao desmontar |

---

## Concluído (v0.7.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **RBAC** | Três roles — `admin`, `operator`, `viewer` — aplicados server-side em todos os endpoints via dependências FastAPI |
| **Hierarquia de roles** | `admin` (nível 3) ≥ `operator` (nível 2) ≥ `viewer` (nível 1); dependências `require_admin` e `require_operator` aplicadas por endpoint |
| **API de gerenciamento de usuários** | `GET /api/users`, `POST /api/users`, `PATCH /api/users/{id}`, `POST /api/users/{id}/reset-password`, `DELETE /api/users/{id}` — somente admin |
| **Proteção do último admin** | Não é possível desativar ou excluir a última conta admin ativa |
| **Modelo de log de auditoria** | Tabela `audit_logs`: `user_id`, `action`, `resource_type`, `resource_id`, `status`, `ip_address`, `user_agent`, `metadata` mascarado, `created_at` |
| **API de log de auditoria** | `GET /api/audit-logs` com filtros (user_id, action, resource_type, status, since, until, limit) — somente admin |
| **Cobertura de auditoria** | Sucesso/falha de login, CRUD de jobs + execução, CRUD de webhooks + reprocessamento, ack/resolve de alertas, CRUD de canais de notificação + teste, CRUD de templates, CRUD de políticas de escalonamento + passos, geração de relatórios, gerenciamento de usuários |
| **Mascaramento de metadados sensíveis** | Senhas, tokens, chaves de API, URLs de webhook e chaves de criptografia removidos dos metadados de auditoria antes da persistência |
| **Rastreamento de `last_login_at`** | Modelo de usuário registra timestamp do último login bem-sucedido |
| **Frontend: Página de Usuários** | Página somente admin com tabela de usuários, formulário de criação, seletor de role inline, ativar/desativar, reset de senha e excluir |
| **Frontend: Página de Logs de Auditoria** | Página somente admin com controles de filtro (ação, tipo de recurso, status, intervalo de datas) e tabela de logs paginada |
| **Frontend: `AdminRoute`** | Guard de rota que redireciona não-admins para `/`; usuários não autenticados para `/login` |
| **Frontend: `isAdmin` / `isOperator`** | Booleanos computados no `AuthContext`; sidebar oculta itens de navegação admin para não-admins |
| **Testes de RBAC** | 20 testes de backend cobrindo limites de permissão de viewer/operator/admin |
| **Testes de log de auditoria** | 5 testes de backend: eventos de login, auditoria de job, mascaramento de metadados, queries de filtro |
| **Testes de gerenciamento de usuários** | 9 testes de backend: CRUD completo, proteção do último admin, sem exposição de `password_hash` |
| **Testes de frontend** | 8 novos testes de frontend (UsersPage e AuditLogsPage) — total de 65 passando |

---

## Concluído (v0.6.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **Canal webhook Slack** | Tipo `slack_webhook` com formato Slack attachments e código de cor por severidade |
| **Canal Telegram** | Tipo `telegram_message` com Bot API e formatação Markdown |
| **Templates de notificação** | Templates específicos por severidade ou catch-all com customização de título/body e fallback embutido |
| **Políticas de escalonamento** | Políticas em múltiplos passos: passo 0 despacha imediatamente; passos posteriores disparam em ciclo APScheduler de 60 segundos |
| **Criptografia de credenciais** | Criptografia AES Fernet para todas as configurações de canal; variável de ambiente `NOTIFICATION_ENCRYPTION_KEY`; migração de JSON simples legado |
| **Frontend: Página de Templates** | Criar, editar e excluir templates de notificação pela interface |
| **Frontend: Página de Escalonamento** | Construtor de políticas em múltiplos passos com seletor de canal e delay por passo |
| **Mascaramento de credenciais** | URL Slack, token Telegram e senha SMTP removidos antes de qualquer resposta da API, log ou registro de erro de entrega |

---

## Concluído (v0.5.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **Canais de notificação** | API e página frontend de CRUD para canais de webhook Discord, email SMTP e webhook customizado |
| **Teste de canal** | Endpoint de teste protegido que envia uma notificação de exemplo e registra o resultado de entrega |
| **Integração de entrega de alertas** | Alertas críticos de jobs e webhooks despacham notificações pelos canais ativos |
| **Histórico de entregas** | Registros de entrega de notificação armazenam sucesso/falha, metadados do canal, timestamps e erros mascarados |
| **Mascaramento de segredos** | Respostas da API e UI mostram configuração mascarada do canal; erros de entrega são removidos antes da persistência |
| **Testes de notificação** | Testes de backend cobrem CRUD de canal, envios de teste, despacho de alertas e falhas mascaradas; testes de frontend cobrem a página de canais |

---

## Concluído (v0.4.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **Worker Celery** | Processo worker dedicado executa jobs HTTP fora do processo da API |
| **Fila Redis** | Broker/backend de resultado Redis configurado com `REDIS_URL` |
| **Execuções manuais enfileiradas** | `POST /api/jobs/{id}/run` cria uma execução `queued` e despacha uma task Celery |
| **Execuções agendadas enfileiradas** | APScheduler mantém o timing do agendamento mas despacha trabalho para a fila |
| **Estados de retry** | Execuções podem passar por `queued`, `running`, `retrying`, `success`, `failure` e `timeout` |
| **Healthchecks do worker** | Arquivos Compose de desenvolvimento e produção incluem healthchecks de Redis e worker |
| **Testes do worker** | Testes de backend cobrem enfileiramento, execução pelo worker, alertas de falha final e estado retrying |

---

## Concluído (v0.3.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **Guia de deploy em produção** | Deploy passo a passo em VPS com Docker Compose, domínio, HTTPS e checklist de produção |
| **Proxy reverso Caddy** | Template `Caddyfile` com HTTPS automático, headers de segurança e roteamento por caminho |
| **`docker-compose.prod.yml`** | Compose de produção separado: Caddy nas portas 80/443, backend/frontend sem exposição, PostgreSQL apenas na rede interna |
| **Healthchecks de containers** | Healthchecks em todos os serviços (backend, frontend, db, Caddy) com `restart: always` |
| **`.env.production.example`** | Template de ambiente de produção com todas as variáveis obrigatórias documentadas |
| **Guia de backup e restore** | Comandos de dump/restore do PostgreSQL e exemplo de cron |
| **Procedimento de atualização** | Git pull + rebuild + auto-migração documentados |
| **Guia de logs e troubleshooting** | Problemas comuns, exec de container, transmissão de logs |
| **Targets `prod-*` do Makefile** | `prod-up`, `prod-down`, `prod-logs`, `prod-validate` |
| **CI de configuração de produção** | Workflow GitHub Actions valida sintaxe do `docker-compose.prod.yml` e do `Caddyfile` |
| **Endpoint de health aprimorado** | `/api/health` agora reporta `database: "ok"/"error"` para observabilidade |

---

## Concluído (v0.2.0)

| Funcionalidade | Detalhes |
| --- | --- |
| **Autenticação JWT** | Endpoint de login, admin bootstrap, validação de token Bearer em todas as rotas protegidas |
| **Interface de gerenciamento de jobs** | Criar, editar, pausar, ativar, executar e excluir jobs pelo frontend |
| **Interface de execuções** | Lista de histórico com filtros de status/job, visão de detalhe com dados mascarados de requisição/resposta |
| **Proteção SSRF** | Bloqueia URLs de jobs direcionadas a faixas privadas/internas; verificação de resolução DNS; configurável |
| **Rate limiting de webhooks** | Rate limiter in-memory por IP e por slug; HTTP 429 em excesso; limite configurável |

---

## Concluído (v0.1.0)

Estas funcionalidades estão implementadas, testadas e validadas no MVP atual.

| Funcionalidade | Detalhes |
| --- | --- |
| **Backend FastAPI** | REST API, CORS, logging estruturado, sessões async SQLAlchemy |
| **PostgreSQL + Alembic** | Versionamento de schema, migração inicial cobrindo todas as tabelas de domínio |
| **Executor HTTP** | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` com timeout configurável; dados sensíveis mascarados antes do armazenamento |
| **APScheduler** | Agendamento in-process por intervalo (segundos) e cron (expressão de cinco campos); agendamento atualizado nas mudanças de job |
| **Histórico de execuções** | Toda execução armazenada com status, tempos, metadados de requisição mascarados e prévia de resposta |
| **Dashboard + API de stats** | Métricas em tempo real: jobs ativos, execuções/falhas em 24h, taxa de sucesso, gráfico de 7 dias (Recharts) |
| **Receptor de webhooks** | CRUD, endpoints por slug, validação de token SHA-256, histórico de eventos, reprocessamento manual |
| **Alertas internos** | Criados automaticamente em falhas de job; fluxos de reconhecimento e resolução; filtro por status |
| **Relatórios operacionais** | Gerar para qualquer período; exportar como JSON, Markdown ou CSV; snapshots históricos estáveis |
| **Frontend React** | Páginas de Dashboard, Webhooks, Alertas e Relatórios; TanStack Query, React Router, Tailwind CSS |
| **Docker Compose** | Backend, frontend e PostgreSQL com healthcheck; migrações executadas na inicialização do backend |
| **GitHub Actions CI** | Pipelines de backend (ruff + pytest) e frontend (ESLint + Vitest + build) |
| **Suítes de teste** | 109 testes de backend, 31 testes de frontend — todos passando |
| **Mascaramento de segredos** | Headers e campos JSON do body mascarados antes de qualquer escrita no banco; cobertura de testes dedicada |
| **Script de seed de demonstração** | `make seed` popula dados de demonstração para screenshots e exploração local |

---

## Futuro (planejado, sem data)

Estas funcionalidades estão planejadas mas ainda não estão em desenvolvimento ativo.

| Funcionalidade | Descrição |
| --- | --- |
| **Provedores de notificação adicionais** | PagerDuty, OpsGenie e opções de entrega mais ricas específicas por provedor |
| **Logs em tempo real** | ~~Entregue em v0.8.0~~ |
| **RBAC** | ~~Entregue em v0.7.0~~ |
| **Interface avançada de política de retry** | ~~Entregue em v1.0.0~~ |
| **Relatórios em PDF** | Exportar relatórios operacionais como PDF além de JSON, Markdown e CSV |
| **Multi-workspace** | Isolamento de namespace para times ou projetos dentro de uma única instância |
| **Registry de imagens Docker** | ~~Entregue em v0.9.0~~ |
| **Log de auditoria** | ~~Entregue em v0.7.0~~ |

---

## Fora do Escopo deste Projeto

Os seguintes itens não são objetivos do AutoFlowOps:

- Plataforma SaaS multi-tenant com cobrança
- Construtor visual de fluxos low-code / no-code
- Aplicativo desktop ou móvel
- Substituto para plataformas completas como n8n, Zapier ou Temporal
