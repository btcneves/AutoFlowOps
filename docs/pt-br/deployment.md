# Guia de Deploy

Este guia cobre três formas de rodar o AutoFlowOps:

1. **Baixar do registry** — mais rápido; baixa imagens pré-compiladas do GHCR. Sem etapa de build.
2. **Build a partir do código-fonte** — build local completo usando Docker Compose.
3. **Produção em um VPS** — proxy reverso Caddy com HTTPS automático.

---

## Opção 1 — Baixar do GitHub Container Registry (GHCR)

O AutoFlowOps publica imagens Docker versionadas no GHCR a cada tag de release. Nenhum build local é necessário.

### Imagens

| Imagem | Caminho no registry |
| --- | --- |
| Backend | `ghcr.io/btcneves/autoflowops-backend` |
| Frontend | `ghcr.io/btcneves/autoflowops-frontend` |

Tags disponíveis: `latest`, `vX.Y.Z`, `X.Y.Z`, `X.Y` (ex: `v1.0.0`, `1.0.0`, `1.0`).

### Setup rápido (interativo)

```bash
git clone https://github.com/btcneves/autoflowops.git
cd autoflowops
bash scripts/setup.sh
```

O script:

1. Verifica se Docker e Docker Compose estão instalados
2. Copia `.env.example` para `.env` se não existir
3. Solicita uma tag de imagem (padrão: `latest`)
4. Baixa `autoflowops-backend` e `autoflowops-frontend` do GHCR
5. Inicia o stack com `docker-compose.registry.yml`
6. Aguarda o endpoint de health do backend e o frontend responderem
7. Imprime URLs dos serviços

### Não-interativo (CI / ambientes com script)

```bash
IMAGE_TAG=v1.0.0 bash scripts/setup.sh
```

### Atalhos do Makefile

```bash
# Baixar imagens (IMAGE_TAG padrão é latest)
make pull

# Iniciar stack usando imagens GHCR
IMAGE_TAG=v1.0.0 make registry-up

# Parar
make registry-down

# Transmitir logs
make registry-logs
```

### Fixar uma versão específica

```bash
IMAGE_TAG=v1.0.0 docker compose -f docker-compose.registry.yml up -d
```

### Atualizar para uma nova versão

```bash
IMAGE_TAG=v1.0.0 make pull
IMAGE_TAG=v1.0.0 make registry-down
IMAGE_TAG=v1.0.0 make registry-up
```

O container do backend executa `alembic upgrade head` na inicialização e aplica qualquer migração pendente automaticamente.

---

## Opção 2 — Build a partir do código-fonte (Docker Compose local)

---

## Desenvolvimento Local

### Requisitos

- Docker + Docker Compose

### Iniciar

```bash
cp .env.example .env
docker compose up --build
```

O backend executa `alembic upgrade head` automaticamente antes de iniciar. Serviços:

| Serviço | URL |
| --- | --- |
| Frontend | <http://localhost:3000> |
| Backend API | <http://localhost:8000> |
| Swagger docs | <http://localhost:8000/docs> |
| ReDoc | <http://localhost:8000/redoc> |
| Redis | `localhost:6379` |

### Verificar

```bash
curl http://localhost:8000/api/health
```

Esperado: `{"status":"ok","app":"AutoFlowOps","env":"development","database":"ok"}`

### Dados de demonstração

```bash
make seed
```

---

## Deploy em Produção em um VPS

Esta seção cobre o deploy do AutoFlowOps em um VPS Linux com domínio customizado e HTTPS automático via Caddy.

### Arquitetura

```text
Internet
  └─> Caddy (portas 80 / 443, TLS)
        ├─> /api/* → backend:8000  (FastAPI)
        └─> /*     → frontend:3000 (Vite preview)
              ├─> worker (Celery, interno apenas)
              ├─> Redis (interno apenas)
              └─> PostgreSQL (rede interna apenas, não exposto)
```

O Caddy gerencia provisionamento e renovação de certificados TLS automaticamente via Let's Encrypt. O backend e o frontend não são acessíveis diretamente da internet — apenas o Caddy é exposto.

### Requisitos do Servidor

| Requisito | Mínimo |
| --- | --- |
| SO | Ubuntu 22.04 LTS (ou qualquer distro moderna baseada em Debian) |
| RAM | 1 GB |
| CPU | 1 vCPU |
| Disco | 10 GB |
| Docker | 24+ |
| Docker Compose | v2.20+ |

As portas 80 e 443 devem estar abertas no firewall do servidor (UFW, iptables ou security group de cloud).

### 1. Configuração de DNS

Crie um registro A apontando seu domínio para o IP público do servidor:

```text
autoflowops.seudominio.com → <ip-publico-do-servidor>
```

Verifique a propagação antes de prosseguir (o Caddy precisa resolver o domínio para obter um certificado):

```bash
dig +short autoflowops.seudominio.com
```

### 2. Instalar Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
```

### 3. Clonar o Repositório

```bash
git clone https://github.com/btcneves/autoflowops.git
cd autoflowops
```

### 4. Configurar o Ambiente de Produção

```bash
cp .env.production.example .env.production
```

Edite `.env.production` e substitua todos os placeholders `REPLACE_WITH_*` por valores reais. Gere segredos fortes com:

```bash
openssl rand -hex 32
```

Variáveis principais a definir:

| Variável | Exemplo | Notas |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | *(aleatório)* | Senha do banco PostgreSQL |
| `POSTGRES_USER` | `autoflowops` | Usuário do PostgreSQL |
| `POSTGRES_DB` | `autoflowops` | Nome do banco PostgreSQL |
| `DATABASE_URL` | `postgresql+psycopg://autoflowops:<senha>@db:5432/autoflowops` | Deve corresponder aos valores `POSTGRES_*` |
| `REDIS_URL` | `redis://redis:6379/0` | URL do broker/backend Redis interno |
| `APP_SECRET_KEY` | *(hex de 64 chars)* | Segredo geral da aplicação |
| `JWT_SECRET_KEY` | *(hex de 64 chars)* | Assina tokens JWT — use um valor diferente de `APP_SECRET_KEY` |
| `FRONTEND_URL` | `https://autoflowops.seudominio.com` | Origem CORS permitida |
| `ADMIN_EMAIL` | `admin@seudominio.com` | Email da conta admin inicial |
| `ADMIN_PASSWORD` | *(senha forte)* | Senha da conta admin inicial — altere após o primeiro login |

### 5. Configurar o Caddy

Edite `Caddyfile` e substitua `autoflowops.yourdomain.com` pelo seu domínio, e `webmaster@yourdomain.com` por um endereço de email real (usado pelo Let's Encrypt para notificações de certificado):

```caddyfile
{
    email webmaster@seudominio.com
}

autoflowops.seudominio.com {
    ...
}
```

### 6. Iniciar o Stack de Produção

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Na primeira inicialização, o backend:

1. Executa `alembic upgrade head` para aplicar migrações do banco
2. Cria a conta admin a partir de `ADMIN_EMAIL` / `ADMIN_PASSWORD`
3. Carrega jobs agendados do banco
4. Inicia o worker para que jobs manuais e agendados possam executar
5. Carrega canais de notificação do banco quando alertas são despachados

### 7. Verificar

```bash
# Health check da API (esperar database: "ok")
curl https://autoflowops.seudominio.com/api/health

# Frontend (esperar 200)
curl -I https://autoflowops.seudominio.com
```

Se o certificado ainda não foi provisionado (Caddy leva ~30 segundos na primeira inicialização), aguarde e tente novamente.

### 8. Primeiro Login

1. Abra `https://autoflowops.seudominio.com` no browser.
2. Faça login com `ADMIN_EMAIL` e `ADMIN_PASSWORD`.
3. Altere a senha do admin imediatamente via API ou atualizando `ADMIN_PASSWORD` em `.env.production` e reiniciando — note que `ADMIN_PASSWORD` é usada apenas na primeira inicialização; para alterar a senha após o bootstrap, use a API ou atualize o banco diretamente.

---

## Targets do Makefile (Produção)

```bash
make prod-up        # Inicia o stack de produção em background
make prod-down      # Para o stack de produção
make prod-logs      # Transmite logs de todos os serviços de produção
make prod-validate  # Valida a sintaxe do docker-compose.prod.yml e do Caddyfile
```

---

## Referência de Variáveis de Ambiente

| Variável | Padrão | Obrigatório em Prod | Notas |
| --- | --- | --- | --- |
| `POSTGRES_DB` | — | Sim | Nome do banco PostgreSQL |
| `POSTGRES_USER` | — | Sim | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | — | Sim | Senha do PostgreSQL |
| `APP_NAME` | `AutoFlowOps` | Não | Nome de exibição |
| `APP_ENV` | `development` | Sim (`production`) | Controla comportamento de debug/logging |
| `APP_DEBUG` | `false` | Não | Mantenha `false` em produção |
| `APP_SECRET_KEY` | `change-me` | Sim | Substitua antes de qualquer deploy |
| `DATABASE_URL` | Fallback SQLite | Sim | Deve usar o hostname `db` |
| `REDIS_URL` | `redis://redis:6379/0` | Sim | Deve usar o hostname `redis` no Compose |
| `JOB_EXECUTION_MODE` | `celery` | Não | Use `celery` em deployments normais; `inline` é para testes isolados |
| `FRONTEND_URL` | `http://localhost:3000` | Sim | Origem CORS permitida |
| `JWT_SECRET_KEY` | `change-me` | Sim | Substitua antes de qualquer deploy |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Não | Tempo de vida do token em minutos |
| `ADMIN_EMAIL` | `admin@autoflowops.local` | Sim | Email do admin bootstrap |
| `ADMIN_PASSWORD` | `changeme` | Sim | Senha do admin bootstrap |
| `ADMIN_NAME` | `Admin` | Não | Nome de exibição do admin bootstrap |
| `ENABLE_SSRF_PROTECTION` | `true` | Não | Mantenha `true` em produção |
| `ALLOW_PRIVATE_NETWORK_TARGETS` | `false` | Não | Mantenha `false` em produção |
| `WEBHOOK_RATE_LIMIT_PER_MINUTE` | `60` | Não | Rate limit de webhook por IP |
| `LOG_LEVEL` | `INFO` | Não | `DEBUG`, `INFO`, `WARNING` |
| `DEFAULT_TIMEZONE` | `America/Sao_Paulo` | Não | Timezone operacional |

Os canais de notificação são configurados na UI ou API após o login. Nenhuma credencial de provedor é necessária em `.env.production`; armazene apenas URLs de webhook dedicadas ou credenciais SMTP criadas para o AutoFlowOps.

---

## Backup e Restore

### Backup do PostgreSQL

```bash
# Criar dump com timestamp
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U autoflowops autoflowops \
  > backup_$(date +%Y%m%d_%H%M%S).sql
```

Armazene o dump em um local fora do servidor (S3, object storage, host remoto). Para backups automatizados, agende o comando com cron:

```bash
# crontab -e
0 3 * * * cd /srv/autoflowops && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U autoflowops autoflowops > /srv/backups/autoflowops_$(date +\%Y\%m\%d).sql
```

### Restore do PostgreSQL

```bash
# Parar o backend primeiro para evitar conexões ativas
docker compose -f docker-compose.prod.yml stop backend

# Restaurar a partir do dump
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U autoflowops autoflowops < backup_20260101_030000.sql

# Reiniciar
docker compose -f docker-compose.prod.yml start backend
```

---

## Atualizar para uma Nova Versão

```bash
# 1. Baixar o código mais recente
git pull origin main

# 2. Rebuildar e reiniciar
docker compose -f docker-compose.prod.yml up -d --build

# O entrypoint do backend executa "alembic upgrade head" automaticamente antes de iniciar.
# Se as migrações falharem, o container sai — verifique os logs antes de prosseguir.

# 3. Verificar
curl https://autoflowops.seudominio.com/api/health
```

Se uma migração falhar:

```bash
# Inspecionar logs de migração
docker compose -f docker-compose.prod.yml logs backend

# Executar migrações manualmente dentro do container
docker compose -f docker-compose.prod.yml run --rm backend \
  sh -c "alembic upgrade head"
```

---

## Logs e Troubleshooting

### Ver logs

```bash
# Todos os serviços
docker compose -f docker-compose.prod.yml logs -f

# Serviço específico
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f caddy
docker compose -f docker-compose.prod.yml logs -f db
docker compose -f docker-compose.prod.yml logs -f redis
```

### Verificar status dos containers

```bash
docker compose -f docker-compose.prod.yml ps
```

### Problemas comuns

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `502 Bad Gateway` do Caddy | Container do backend não está saudável | `logs backend` — verifique erro de conexão com banco ou falha de migração |
| Certificado TLS não emitido | DNS não propagado ou porta 80 bloqueada | Verifique registro A do DNS; verifique firewall |
| `database: "error"` em `/api/health` | Container do banco inativo ou credenciais incorretas | `logs db`; verifique se `DATABASE_URL` corresponde às variáveis `POSTGRES_*` |
| Jobs manuais ficam em `queued` | Worker ou Redis indisponível | `logs worker`; `logs redis`; verifique `REDIS_URL` |
| Backend reiniciando continuamente | Erro de migração na inicialização | `logs backend`; corrija a migração, depois `docker compose -f docker-compose.prod.yml up -d --build` |
| `403 Forbidden` no recebimento de webhook | Mismatch de token ou webhook pausado | Verifique header `X-Webhook-Token`; verifique status do webhook |
| `429 Too Many Requests` | Rate limit excedido | Aguarde um minuto ou aumente `WEBHOOK_RATE_LIMIT_PER_MINUTE` |
| Teste de notificação falha | Problema de URL do provedor, credenciais SMTP ou firewall de saída | Verifique configuração do canal, credenciais do provedor e logs do backend |
| Badge WS fica em "Conectando…" | Backend indisponível ou `VITE_API_BASE_URL` incorreto | Verifique se `VITE_API_BASE_URL` está configurado corretamente; verifique console do browser para erros WS |
| Eventos WS não recebidos | Redis não está rodando | `logs redis`; verifique `REDIS_URL`; logs do backend mostram "Redis WS subscriber exited" se desconectado |
| `docker pull` falha com 403 | Pacote GHCR é privado | Vá para repositório → Packages → torne o pacote público, ou faça `docker login ghcr.io` com um token |
| Stack inicia mas mostra versão antiga | `IMAGE_TAG` não definido ou `latest` em cache | Execute `make pull IMAGE_TAG=v1.0.0` depois `make registry-up IMAGE_TAG=v1.0.0` |

### Entrar em um container

```bash
docker compose -f docker-compose.prod.yml exec backend sh
docker compose -f docker-compose.prod.yml exec worker sh
docker compose -f docker-compose.prod.yml exec db psql -U autoflowops autoflowops
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
```

---

## Checklist de Produção

Execute esta lista antes de expor a instância aos usuários.

- [ ] `POSTGRES_PASSWORD` definido com um valor aleatório forte
- [ ] `APP_SECRET_KEY` definido com uma string hex aleatória de 64 caracteres
- [ ] `JWT_SECRET_KEY` definido com uma string hex aleatória de 64 caracteres diferente
- [ ] `ADMIN_EMAIL` e `ADMIN_PASSWORD` definidos com valores reais (não os padrões)
- [ ] `FRONTEND_URL` definido para o domínio HTTPS público
- [ ] Credenciais de `DATABASE_URL` correspondem a `POSTGRES_USER` / `POSTGRES_PASSWORD`
- [ ] `REDIS_URL` definido como `redis://redis:6379/0`
- [ ] `.env.production` **não** commitado no controle de versão
- [ ] Domínio do Caddyfile atualizado (não `yourdomain.com`)
- [ ] Email do Caddyfile atualizado (não `webmaster@yourdomain.com`)
- [ ] Registro A do DNS apontando para o IP público do servidor
- [ ] Portas 80 e 443 abertas no firewall do servidor
- [ ] Porta 5432 (PostgreSQL) **não** exposta publicamente (ausente no `docker-compose.prod.yml`)
- [ ] Porta 6379 (Redis) **não** exposta publicamente (ausente no `docker-compose.prod.yml`)
- [ ] `curl https://seudominio.com/api/health` retorna `{"status":"ok",...,"database":"ok"}`
- [ ] Healthcheck do worker está passando e jobs manuais saem do status `queued`
- [ ] Primeiro login bem-sucedido; senha do admin alterada ou anotada
- [ ] Estratégia de backup em funcionamento (cron job ou agendamento manual)
