# Arquitetura

O AutoFlowOps é um dashboard de automação self-hosted composto por um backend FastAPI, um worker Celery, fila Redis, frontend React e persistência em PostgreSQL. A API gerencia os fluxos de requisição/resposta, o gerenciamento de canais de notificação e o agendamento; o worker gerencia a execução HTTP dos jobs. Um stream WebSocket em tempo real envia eventos de domínio (mudanças de estado de execução, novos alertas) aos clientes conectados no browser conforme ocorrem.

---

## Componentes em Execução

| Componente | Responsabilidade |
| --- | --- |
| **Frontend** | Interface no browser — dashboard, webhooks, alertas, canais de notificação e relatórios |
| **Backend API** | REST API, validação de requisições, acesso ao banco de dados e fluxos operacionais |
| **Endpoint WebSocket** | `GET /ws/events` — stream autenticado via JWT; envia eventos `execution.started`, `execution.completed` e `alert.created` em tempo real |
| **Worker Celery** | Executa jobs HTTP enfileirados, gerencia retries e registra resultados de execução |
| **Redis** | Broker/backend de resultado do Celery e canal Pub/Sub (`autoflowops:events`) para fan-out em tempo real |
| **PostgreSQL** | Armazenamento persistente de todos os dados de domínio |
| **APScheduler** | Agendamento in-process de intervalo e cron para jobs ativos; despacha trabalho para o Redis |
| **HTTP runner** | Lógica de execução compartilhada pelo worker: timeout, mascaramento, proteção SSRF e alertas |
| **Serviço de notificação** | Envia alertas críticos para webhooks Discord, SMTP ou webhooks customizados e registra resultados de entrega |

---

## Fluxo de Requisição de Alto Nível

```text
Browser
  └─> Frontend React/Vite (porta 3000)
        ├─> FastAPI REST API (porta 8000)         [HTTP/JSON]
        │     ├─> SQLAlchemy async session
        │     │     └─> PostgreSQL (porta 5432)
        │     ├─> APScheduler (in-process)
        │     │     └─> Fila Redis
        │     │           └─> Worker Celery
        │     ├─> Receptor de webhooks
        │     └─> Serviço de entrega de notificações
        └─> FastAPI WebSocket (porta 8000 /ws/events)   [push WS]
              └─> Redis Pub/Sub (canal: autoflowops:events)
                    ├─ publicado pelo http_runner (caminho APScheduler)
                    └─ publicado pelo worker Celery (caminho manual/cron)
```

---

## Deploy em Produção

A topologia de produção mantém os serviços de backend, frontend e PostgreSQL em uma rede Docker privada e expõe apenas o Caddy à internet pública.

```text
Internet
  └─> Caddy (80/443, HTTPS automático)
        ├─> /api/*, /docs, /redoc, /openapi.json → backend:8000
        └─> todo o resto                          → frontend:3000

Rede interna Docker
  ├─> backend:8000
  ├─> frontend:3000
  ├─> worker
  ├─> redis:6379
  └─> db:5432
```

O `docker-compose.prod.yml` remove a publicação direta de portas do host para PostgreSQL, Redis, backend, worker e frontend. O Caddy encerra o TLS, define headers de segurança e roteia o tráfego por caminho. O endpoint de health do backend inclui `database: "ok"` ou `database: "error"` para que healthchecks de containers e monitores externos possam distinguir acessibilidade da API de conectividade do banco de dados.

Veja [docs/pt-br/deployment.md](deployment.md) para o guia completo de deploy em VPS.

---

## Modelo de Dados

O schema Alembic cria as seguintes tabelas:

| Tabela | Finalidade |
| --- | --- |
| `jobs` | Configuração do job HTTP, metadados de agendamento, timestamps de última/próxima execução |
| `executions` | Histórico de execuções: metadados da requisição, headers/body mascarados, prévia de respostas, erros |
| `webhooks` | Definições de webhooks de entrada: slug, token com hash, status |
| `webhook_events` | Eventos individuais recebidos em cada endpoint de webhook |
| `alerts` | Alertas operacionais internos gerados por falhas ou criados manualmente |
| `notification_channels` | Destinos externos de notificação e configuração mascarada do canal |
| `notification_deliveries` | Resultados de entrega por alerta para os canais de notificação configurados |
| `reports` | Conteúdo canônico salvo do relatório (JSON) e metadados |
| `users` | Contas autenticadas com roles (`admin`, `operator`, `viewer`), hash bcrypt da senha e timestamp `last_login_at` |
| `audit_logs` | Registro imutável append-only de ações sensíveis: ator, nome da ação, referência de recurso, status, endereço IP, user agent e metadados mascarados |

---

## Controle de Acesso por Roles

Três roles são aplicados server-side. O nível de role é comparado como inteiro para que a hierarquia seja herdável:

| Role | Nível | Capacidades |
| --- | --- | --- |
| `admin` | 3 | Todos os endpoints — gerenciamento de usuários, logs de auditoria e tudo abaixo |
| `operator` | 2 | Criar/editar/excluir jobs, executar jobs, gerenciar webhooks, reconhecer/resolver alertas, testar canais de notificação, gerar relatórios |
| `viewer` | 1 | Acesso somente leitura a todos os dados de domínio; sem operações de escrita |

Cadeia de dependências FastAPI:

```text
Requisição autenticada (JWT Bearer)
  └─> get_current_user          → verifica token, carrega User do banco
        ├─> (sem dep extra)     → endpoints acessíveis por viewer
        ├─> require_operator    → nível >= 2; retorna 403 caso contrário
        └─> require_admin       → nível >= 3; retorna 403 caso contrário
```

Ambos `require_operator` e `require_admin` são definidos em `backend/app/dependencies.py` e aplicados por endpoint via `Depends()`.

---

## Fluxo do Log de Auditoria

Toda ação sensível escreve um registro `AuditLog` na mesma sessão do banco de dados que a operação primária:

```text
Requisição API autenticada
  ├─> executar operação no banco (criar job, excluir usuário etc.)
  ├─> session.flush()              # atribui PK às novas linhas sem fazer commit
  ├─> log_action(session, ...)     # insere linha AuditLog; mascara metadados sensíveis
  └─> session.commit()             # faz commit da operação primária e da entrada de auditoria atomicamente
```

O serviço `log_action` (`backend/app/services/audit.py`) remove chaves que correspondem ao conjunto de chaves sensíveis antes de escrever `metadata` no banco. Chaves sensíveis incluem: `password`, `password_hash`, `secret`, `token`, `api_key`, `webhook_url`, `bot_token`, `smtp_password`, `encryption_key`.

---

## Modelo de Agendamento

O agendador é carregado na inicialização do backend e persiste durante o tempo de vida do processo da API. Ele não executa requisições HTTP diretamente; cria registros de execução enfileirados e despacha tasks Celery pelo Redis.

| Tipo de agendamento | Formato da expressão | Exemplo |
| --- | --- | --- |
| `manual` | Nenhum — acionado apenas via `POST /api/jobs/{id}/run` | — |
| `interval` | Segundos como string de inteiro simples | `"300"` → a cada 5 minutos |
| `cron` | Expressão crontab de cinco campos | `"*/10 * * * *"` → a cada 10 minutos |

Quando o status de um job muda para `paused`, ele é removido do agendador. Quando retorna a `active`, é re-registrado com a mesma expressão.

> **Nota multi-instância:** a execução HTTP é tratada pelos workers, mas o timing do agendamento ainda fica no processo da API. Execute uma réplica da API proprietária do agendador até que a liderança do agendador seja externalizada.

---

## Fluxo: Execução de Job HTTP

### Acionamento manual

```text
POST /api/jobs/{id}/run
  └─> carrega job do banco
        ├─> cria Execution(status="queued", trigger_type="manual")
        └─> enfileira task Celery no Redis
              └─> worker carrega job + execution
                    ├─> status="running"
                    ├─> httpx.AsyncClient.request(method, url, headers, body, timeout)
                    ├─> mascara headers e campos sensíveis do body
                    ├─> atualiza Execution com tempos, prévia de resposta e status
                    ├─> retry com status="retrying" enquanto houver tentativas
                    └─> em falha/timeout final
                          └─> cria registro Alert (severity="error", source_type="job_execution")
```

### Acionamento agendado

```text
APScheduler dispara _run_scheduled_job(job_id)
  └─> abre sessão async do banco
        └─> carrega job do banco
              ├─> cria Execution(status="queued", trigger_type="scheduled")
              ├─> enfileira task Celery no Redis
              └─> atualiza job.next_run_at a partir do agendador
```

Status de execução:

| Status | Significado |
| --- | --- |
| `queued` | API ou agendador criou a execução e a despachou para o Redis |
| `running` | Worker iniciou a tentativa de requisição HTTP |
| `retrying` | Tentativa falhou e o Celery agendou outra tentativa |
| `success` | Tentativa final retornou status HTTP de sucesso |
| `failure` | Tentativa final retornou status de erro ou lançou exceção não relacionada a timeout |
| `timeout` | Tentativa final excedeu o tempo limite |

---

## Fluxo: Recepção de Webhook

```text
POST /api/webhooks/{slug}/receive
  ├─> busca webhook pelo slug → 404 se não encontrado
  ├─> verifica webhook.status == "active" → 403 se pausado
  ├─> valida header X-Webhook-Token contra hash SHA-256 → 403 se não corresponder
  ├─> mascara headers e campos sensíveis do payload
  ├─> cria registro WebhookEvent (headers_masked, payload, source_ip, received_at)
  ├─> atualiza webhook.last_received_at
  └─> retorna 200 com id do evento
```

---

## Fluxo: Geração de Alertas

Os alertas são criados automaticamente pelo HTTP runner em cada execução com falha:

```text
run_job_http detecta execution.status == "failure"
  └─> cria Alert(
        title      = "Job '<nome>' failed",
        message    = mensagem de erro ou f"HTTP {status_code}",
        severity   = "error",
        source_type = "job_execution",
        source_id  = execution.id,
        status     = "open"
      )
        └─> canais de notificação ativos recebem o alerta crítico
```

---

## Fluxo: Notificações Externas

```text
Alert(severity="error") é criado
  └─> carrega canais de notificação ativos
        ├─> discord_webhook: POST payload do webhook Discord
        ├─> slack_webhook: POST payload do webhook Slack
        ├─> telegram_message: envia mensagem pela Telegram Bot API
        ├─> smtp_email: envia email de texto via SMTP
        └─> custom_webhook: POST payload JSON padrão
              └─> cria NotificationDelivery(status="success" | "failed")
```

---

## Fluxo: Eventos em Tempo Real (WebSocket)

```text
Browser (autenticado)
  └─> handshake WS: GET /ws/events?token=<JWT>
        └─> servidor valida JWT + busca usuário no banco
              ├─> rejeitar (fechar 1008)  se token inválido ou usuário não encontrado
              └─> aceitar → registrar no ConnectionManager

                          [conexão de longa duração]
                                │
Worker Celery / http_runner
  └─> publish_event("execution.started" | "execution.completed" | "alert.created")
        └─> redis.publish("autoflowops:events", JSON)

Task asyncio subscriber no backend
  └─> redis.subscribe("autoflowops:events")
        └─> ao receber mensagem → ConnectionManager.broadcast(message)
              └─> ws.send_text(message) para cada conexão registrada
```

---

## Modelo de Segurança

| Aspecto | Abordagem atual |
| --- | --- |
| Segredos em logs | Headers sensíveis e campos JSON do body mascarados antes de qualquer escrita no banco |
| Tokens de webhook | Armazenados como hashes SHA-256; tokens em texto simples nunca persistidos |
| Arquivo `.env` | Ignorado pelo git; apenas `.env.example` é commitado |
| Autenticação | Tokens JWT Bearer obrigatórios em todas as rotas exceto `/api/health`, `/api/version` e recepção de webhook; WebSocket usa JWT via query parameter |
| Autorização | Controle de acesso por roles: dependências `require_admin` (somente admin) e `require_operator` (operator+) aplicadas por endpoint |
| Trilha de auditoria | Toda escrita sensível é registrada em `audit_logs` atomicamente na mesma sessão do banco; metadados sensíveis mascarados antes da persistência |
| Exposição de senha | `password_hash` nunca retornado em nenhuma resposta da API; schema `UserRead` o omite |
| Senhas | Hash bcrypt; senhas em texto simples nunca armazenadas |
| SSRF | Faixas de IP privadas/reservadas bloqueadas por padrão antes de qualquer execução de job HTTP |
| Rate limiting | Rate limiter in-memory por IP no receptor de webhooks |
| Fila | Redis é interno às redes Docker; payloads de jobs referenciam IDs do banco, não segredos em texto simples |
| Credenciais de notificação | Configuração do canal é mascarada nas respostas da API/UI; deployments devem proteger acesso ao banco e backups do ambiente |

Veja [docs/pt-br/security.md](security.md) para a referência completa de mascaramento.

---

## Limitações Conhecidas (v0.8.0)

- **Agendador in-process.** APScheduler ainda roda dentro do processo do backend. Execute uma réplica da API proprietária do agendador.
- **Retries de worker por execução.** Uma execução enfileirada é atualizada durante as tentativas de retry em vez de criar uma linha de execução por tentativa.
- **Rate limiter in-process.** O rate limiter é resetado na reinicialização do backend e não é compartilhado entre réplicas. Substitua por uma implementação com Redis para deployments de alta disponibilidade.
- **Token WebSocket na URL.** O JWT é passado como query parameter porque APIs WebSocket do browser não suportam headers customizados. Isso significa que o token aparece nos logs de acesso do servidor. Use HTTPS/WSS em produção e minimize o tempo de vida do token.
- **Único subscriber Redis.** Uma task asyncio assina o canal Redis por processo de backend. Em um setup multi-réplica, cada réplica assina independentemente e faz fan-out apenas para seus próprios clientes conectados.
- **Sem refresh tokens.** Tokens JWT de acesso expiram após `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` sem mecanismo de renovação; usuários precisam re-autenticar.
- **Relatórios não são recomputados.** Downloads são gerados a partir do JSON canônico salvo, não recalculados a partir de dados ao vivo.
- **Credenciais de notificação são armazenadas para entrega.** Segredos do canal são mascarados nas respostas e logs de entrega; criptografia Fernet é aplicada em repouso (v0.6.0+), mas o gerenciamento de chaves no nível do banco é responsabilidade do operador.
- **Log de auditoria é append-only por convenção.** Nenhum mecanismo de imutabilidade em nível de linha (por exemplo, row security do PostgreSQL) é aplicado; acesso físico ao banco contorna a trilha de auditoria.
