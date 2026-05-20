# Segurança

Este documento descreve as práticas de segurança integradas ao AutoFlowOps, as limitações conhecidas do MVP atual e recomendações para deployments em produção.

---

## Mascaramento de Segredos

O AutoFlowOps mascara dados sensíveis antes de gravar registros de execução ou eventos de webhook no banco de dados. **Segredos nunca são armazenados em texto simples em logs ou no histórico de execuções.**

### Headers HTTP Mascarados

Qualquer header de requisição cujo nome contenha um dos seguintes padrões é mascarado (case-insensitive):

- `authorization`
- `x-api-key`
- `api-key`
- `token`
- `secret`
- `password`
- `cookie`
- `set-cookie`

Exemplo de valor armazenado:

```json
{
  "Authorization": "Bearer ***MASKED***",
  "Content-Type": "application/json"
}
```

### Campos JSON do Body Mascarados

Qualquer campo JSON do body cuja chave contenha um dos seguintes padrões é mascarado recursivamente (incluindo objetos aninhados):

- `password`, `passwd`, `pwd`
- `token`, `access_token`, `refresh_token`
- `secret`
- `api_key`, `apikey`
- `private_key`
- `authorization`
- `credential`

Bodies não-JSON (texto simples, binário, form data) são armazenados como estão. Verifique que bodies de jobs não-JSON não contêm segredos antes de configurar um job.

### Mascaramento testado

O serviço de mascaramento (`backend/app/services/masking.py`) possui uma suíte de testes dedicada (`backend/tests/test_masking.py`) com 11 testes cobrindo headers, JSON aninhado, bodies não-JSON e casos extremos.

---

## Segurança dos Tokens de Webhook

- Cada endpoint de webhook exige um `secret_token` no momento da criação.
- O token **nunca é armazenado em texto simples**. Apenas seu hash SHA-256 é persistido no banco de dados.
- Requisições de entrada devem incluir o token no header `X-Webhook-Token`. Requisições com token ausente ou incorreto recebem `403 Forbidden`.
- Webhooks pausados rejeitam todas as requisições de entrada independentemente do token.

---

## Segurança do Arquivo de Ambiente

- `.env` está listado no `.gitignore` e **nunca deve ser commitado no controle de versão**.
- Apenas `.env.example` é commitado. Ele contém apenas valores fictícios de placeholder — sem segredos reais.
- Antes de fazer deploy em produção, copie `.env.example` para `.env` e defina valores únicos e fortes para:
  - `APP_SECRET_KEY`
  - `JWT_SECRET_KEY`
  - As credenciais do banco em `DATABASE_URL`
- Nunca compartilhe seu arquivo `.env` publicamente nem o inclua em imagens Docker.

---

## Proteção SSRF (v0.2.0)

Jobs HTTP executam URLs arbitrárias configuradas pelo operador. Para evitar que jobs atinjam serviços internos, o AutoFlowOps bloqueia requisições para faixas de endereços privados e reservados quando `ENABLE_SSRF_PROTECTION=true` (padrão).

Faixas bloqueadas:

- `127.0.0.0/8` — loopback
- `0.0.0.0/8` — não especificado
- `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` — redes privadas RFC-1918
- `169.254.0.0/16` — link-local (incluindo endpoints de metadados de cloud)
- `100.64.0.0/10` — espaço de endereços compartilhado
- `::1/128`, `fc00::/7`, `fe80::/10` — equivalentes IPv6

A verificação é aplicada tanto a endereços IP literais quanto após a resolução DNS, para evitar bypass via registros DNS customizados.

Defina `ALLOW_PRIVATE_NETWORK_TARGETS=true` apenas em ambientes de desenvolvimento local controlados onde você precisa intencionalmente chamar serviços internos.

---

## Rate Limiting (v0.2.0)

O receptor de webhooks (`POST /api/webhooks/{slug}/receive`) possui rate limiting por IP e por slug usando um contador in-memory de janela fixa.

- Limite padrão: `WEBHOOK_RATE_LIMIT_PER_MINUTE=60` requisições por minuto
- Respostas que excedem o limite recebem `429 Too Many Requests` com header `Retry-After`

A implementação atual é in-process e é resetada na reinicialização do backend. Para deployments multi-réplica ou de alto volume, substitua `app/services/rate_limiter.py` por uma implementação com Redis.

---

## Segurança da Fila (v0.4.0)

A execução de jobs HTTP é despachada pelo Redis e processada pelo worker Celery. Os payloads de tasks enfileiradas contêm identificadores do banco de dados e metadados de acionamento; headers e bodies de requisição são carregados do PostgreSQL pelo worker e são mascarados antes de serem escritos no histórico de execuções.

O Compose de produção mantém o Redis na rede interna Docker apenas. Não exponha o Redis à internet pública. Se fizer deploy fora dos arquivos Compose fornecidos, vincule o Redis a uma interface privada e proteja-o com controles de acesso em nível de rede.

---

## Segurança dos Canais de Notificação (v0.5.0)

Os canais de notificação podem conter configurações de entrega sensíveis:

- URLs de webhook Discord
- URLs de webhook Slack
- Tokens de bot Telegram
- Usuários e senhas SMTP
- URLs e headers de webhooks customizados

As respostas da API e o frontend nunca retornam segredos completos de notificação. A configuração do canal é retornada como `config_masked`, e mensagens de erro de entrega são removidas antes de serem armazenadas em `notification_deliveries`.

As credenciais do canal precisam estar disponíveis para o backend para que as notificações possam ser enviadas. Elas são criptografadas em repouso com Fernet, retornadas apenas como valores mascarados, e ainda dependem da proteção da chave de criptografia configurada, do acesso ao banco de dados e dos backups.

Alvos de webhook de notificação customizados são verificados pela mesma proteção SSRF usada pelos jobs HTTP quando `ENABLE_SSRF_PROTECTION=true`.

---

## Controle de Acesso por Roles (v0.7.0)

Três roles são aplicados **server-side** em todos os endpoints de escrita. As verificações de role são aplicadas como dependências FastAPI (`require_admin`, `require_operator`) e não podem ser contornadas modificando o estado do frontend.

### Matriz de Permissões

| Categoria de endpoint | viewer | operator | admin |
| --- | :---: | :---: | :---: |
| Ler jobs, execuções, webhooks, alertas, relatórios | ✓ | ✓ | ✓ |
| Ler canais de notificação, templates, políticas de escalonamento | ✓ | ✓ | ✓ |
| Criar/editar/excluir jobs | — | ✓ | ✓ |
| Executar jobs manualmente | — | ✓ | ✓ |
| Criar/editar/excluir webhooks, reprocessar eventos | — | ✓ | ✓ |
| Reconhecer/resolver alertas | — | ✓ | ✓ |
| Testar canais de notificação | — | ✓ | ✓ |
| Gerar relatórios | — | ✓ | ✓ |
| Criar/editar/excluir canais de notificação | — | — | ✓ |
| Criar/editar/excluir templates | — | — | ✓ |
| Criar/editar/excluir políticas de escalonamento | — | — | ✓ |
| Gerenciamento de usuários | — | — | ✓ |
| Ver logs de auditoria | — | — | ✓ |

### Proteção do último admin

A API impede que a última conta `admin` ativa seja desativada (`PATCH /api/users/{id}`) ou excluída (`DELETE /api/users/{id}`). A verificação conta as contas admin ativas antes de fazer commit da alteração; a operação é rejeitada com `400` se resultaria em zero admins ativos.

---

## Log de Auditoria (v0.7.0)

Toda ação sensível escreve um registro `AuditLog` atomicamente na mesma sessão do banco de dados que a operação primária. O registro não pode ser criado sem também completar a operação primária (e vice-versa), porque ambos compartilham um único `session.commit()`.

### O que é registrado

- **Auth:** sucesso e falha de login (inclui endereço IP e user agent)
- **Jobs:** criar, atualizar, excluir, executar
- **Webhooks:** criar, atualizar, excluir, reprocessar
- **Alertas:** reconhecer, resolver
- **Canais de notificação:** criar, atualizar, excluir, ativar, desativar, testar
- **Templates:** criar, atualizar, excluir
- **Políticas de escalonamento:** criar, atualizar, excluir, adicionar passo, excluir passo
- **Relatórios:** gerar
- **Usuários:** criar, atualizar, excluir, resetar senha

### Mascaramento de metadados na auditoria

O serviço `log_action` remove as seguintes chaves do dict `metadata` antes de gravar em `audit_logs.metadata`:

`password`, `password_hash`, `secret`, `token`, `api_key`, `webhook_url`, `bot_token`, `smtp_password`, `encryption_key`, `config`, `config_encrypted`, `config_masked`

Chaves aninhadas não são percorridas (metadados esperados como shallow). Se uma chave sensível estiver presente, seu valor é substituído por `"[redacted]"`.

### Acesso ao log de auditoria

`GET /api/audit-logs` é restrito a usuários admin. Filtros: `user_id`, `action`, `resource_type`, `status`, `since`, `until`, `limit` (máx 1000, padrão 100). Resultados são ordenados por `created_at` decrescente.

---

## Autenticação (v0.2.0)

Todas as rotas da API exceto `/api/health`, `/api/version` e o receptor de webhooks requerem um token JWT Bearer válido no header `Authorization`.

- Tokens são emitidos por `POST /api/auth/login` usando verificação de email e senha com hash bcrypt
- Senhas têm hash bcrypt; senhas em texto simples nunca são armazenadas
- Expiração do token é controlada por `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (padrão: 60)
- Uma conta admin é inicializada a partir das variáveis de ambiente `ADMIN_EMAIL` / `ADMIN_PASSWORD` na primeira inicialização; altere esses valores antes de qualquer deploy

**Limitação v0.2.0:** apenas um único token de acesso é emitido (sem refresh tokens, sem revogação de token). Para uso em produção, planeje valores de expiração curtos e altere `ADMIN_PASSWORD` imediatamente após o primeiro login.

---

## Limitações Conhecidas (v0.7.0)

| Limitação | Detalhe |
| --- | --- |
| **Rate limiting in-process** | Resets ao reiniciar; não compartilhado entre réplicas. Substitua por rate limiter com Redis para deployments de alta disponibilidade. |
| **Sem revogação de token** | Tokens JWT permanecem válidos até expirar. Logout apenas limpa o token no lado do cliente. |
| **Sem refresh tokens** | Usuários precisam re-autenticar quando o token de acesso expirar. |
| **Timing do agendador in-process** | APScheduler roda dentro do backend e despacha para Redis. Execute uma réplica da API proprietária do agendador. |
| **Rate limiting Redis não implementado** | Redis é usado para Celery. Rate limiting de webhooks permanece in-memory por processo da API. |
| **Credenciais de notificação criptografadas em repouso** | Segredos do canal são criptografados com Fernet (v0.6.0+). A chave de criptografia precisa ser protegida pelo operador; gerenciamento de chaves em nível de banco não é fornecido. |
| **Retry de notificação simples** | Envios com falha são retentados brevemente e registrados; escalonamento e backoff específico por provedor não são implementados. |
| **Prévia de resposta truncada** | Apenas os primeiros 500 bytes do body da resposta são armazenados. |
| **Log de auditoria append-only por convenção** | Sem imutabilidade em nível de linha; acesso direto ao banco contorna a trilha de auditoria. |

---

## Autenticação WebSocket

O stream de eventos WebSocket em `/ws/events` usa autenticação JWT via query parameter porque as APIs `WebSocket` do browser não suportam headers HTTP customizados durante o handshake.

### Implicações

| Aspecto | Detalhe |
| --- | --- |
| **Token na URL** | O JWT aparece nos logs de acesso do servidor e headers de encaminhamento de proxy. Rotacione tokens se os logs forem vazados. |
| **Mitigação** | Use `wss://` (TLS) em produção para que o query string seja criptografado em trânsito. O Caddy lida com isso automaticamente. |
| **Tempo de vida do token** | A expiração padrão é `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (padrão: 60 minutos). Tempos de vida menores reduzem a janela de exposição. |
| **Fechar ao falhar na autenticação** | O servidor fecha a conexão com código 1008 (Policy Violation) se o token estiver ausente, inválido ou o usuário estiver inativo. O frontend para de reconectar neste código. |

### O que os eventos WS contêm

Os frames de eventos carregam apenas identificadores e valores de status:

- `execution_id`, `job_id`, `job_name`, `trigger_type`, `status`, `duration_ms`, `response_status_code`
- `alert_id`, `title`, `severity`

Nenhum header de requisição, conteúdo de body, credenciais, URLs de webhook ou senhas SMTP são incluídos nos payloads de eventos WebSocket.

---

## Recomendações de Produção

O caminho recomendado de produção é `docker-compose.prod.yml` + Caddy, documentado em [docs/pt-br/deployment.md](deployment.md). Propriedades de segurança principais desse setup:

- **Caddy encerra TLS** — HTTPS automático via Let's Encrypt; HTTP redirecionado para HTTPS.
- **Headers de segurança** — `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` e `Referrer-Policy` definidos pelo Caddy.
- **PostgreSQL não exposto** — porta 5432 ausente do `docker-compose.prod.yml`; banco acessível apenas por outros containers na rede Docker interna.
- **Redis não exposto** — porta 6379 ausente do `docker-compose.prod.yml`; Redis acessível apenas por outros containers na rede Docker interna.
- **Backend e frontend não publicados** — apenas o Caddy (portas 80/443) é acessível de fora do Docker.

Passos adicionais de hardening:

1. **Substitua todos os segredos de placeholder** — gere valores fortes para `APP_SECRET_KEY`, `JWT_SECRET_KEY` e `POSTGRES_PASSWORD` usando `openssl rand -hex 32` antes da primeira execução.
2. **Altere a senha do admin inicial** — `ADMIN_PASSWORD` é usada apenas na primeira inicialização. Após criar a conta admin, use uma senha forte e a altere imediatamente após o primeiro login.
3. **Não commite `.env.production`** — está listado no `.gitignore`; verifique que nunca aparece na saída de `git status`.
4. **Firewall** — permita apenas as portas 22 (SSH), 80 e 443 da internet pública. Bloqueie todas as outras portas no nível do firewall.
5. **Mantenha Docker e o SO atualizados** — acompanhe os avisos de segurança para Ubuntu, Docker, PostgreSQL 16 e Redis.
6. **Revise URLs de jobs** — antes de ativar um job que aponta para um serviço interno, verifique se a URL é intencional para evitar SSRF acidental.
7. **Não use tokens reais em demos** — nunca inclua chaves de API, tokens ou segredos reais em configurações de jobs usadas para screenshots ou documentação.
8. **Proteja credenciais de notificação** — use URLs de webhook e credenciais SMTP dedicadas, rotacione-as periodicamente e restrinja o acesso a backups do banco de dados.
9. **Crie uma conta operator com privilégios mínimos** — evite o uso diário da conta admin. Crie uma conta com role `operator` para tarefas operacionais e reserve o `admin` para gerenciamento de usuários e revisão de auditoria.
10. **Revise os logs de auditoria periodicamente** — `GET /api/audit-logs` fornece um histórico completo de ações. Agende revisões periódicas como parte da sua postura de segurança, especialmente após mudanças de privilégio ou resposta a incidentes.

---

## Reporte de Vulnerabilidades

Não abra uma issue pública para relatar uma vulnerabilidade de segurança.

Siga o processo descrito em [SECURITY.md](../../SECURITY.md).
