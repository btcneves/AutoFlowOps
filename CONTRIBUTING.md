# Contributing

Thanks for considering a contribution to AutoFlowOps.

---

## Development Setup

```bash
cp .env.example .env
make up
```

For local development without Docker, see [docs/development.md](docs/development.md).

---

## Before Opening a Pull Request

Run the full verification suite:

```bash
make lint
make test
cd frontend && npm run build
```

All checks must pass before requesting a review.

---

## Commit Style

Use short conventional-style commits:

```text
feat: add report download endpoint
fix: mask webhook authorization header
docs: update deployment guide
test: cover alert resolution flow
ci: update Python version in backend CI
refactor: simplify scheduler trigger logic
```

---

## Pull Request Guidelines

Every PR must include:

- **Objective** — what changes and why
- **Changes summary** — key files affected
- **Test plan** — how the change was verified

Use the PR template. Fill in all sections.

---

## Public Repository Safety Checklist

Before any public contribution:

- [ ] All included content is publication-ready and meets the project's open-source standards
- [ ] No untracked development files, credentials, local paths, or temporary outputs are included
- [ ] Documentation, commits, images, and release notes reflect the maintainer's work directly
- [ ] The contribution reads as the work of a professional open-source maintainer

---

## Security

Do not open public issues for vulnerabilities. Follow [SECURITY.md](SECURITY.md).
