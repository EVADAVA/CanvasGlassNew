# CanvasGlassNew

This repository starts with a minimal secrets policy.

## Credentials and Tokens

- Store real secrets only in local environment files, CI secret storage, or your hosting platform's secret manager.
- Commit only `.env.example` with variable names and empty values.
- Never expose secrets to frontend bundles or commit them to Git.
- Use separate credentials for development, staging, and production.
- Rotate any token that has been pasted into chat, logs, screenshots, or commits.

## Local Development

1. Copy `.env.example` to `.env.local`.
2. Fill in real values in `.env.local`.
3. Keep `.env.local` out of version control.

## CI and Production

- GitHub Actions: use repository or environment secrets.
- Hosting: use the platform's encrypted secret storage.
- Prefer short-lived tokens where possible.

More detail is in `docs/security/secrets.md`.
