# Secrets Policy

## Rules

1. No real credentials in the repository.
2. No secrets in client-side code.
3. No shared production token across multiple environments.
4. No manual secret values inside source files or test fixtures.

## Approved Storage

- Local development: `.env.local`
- CI/CD: GitHub Actions Secrets or Environment Secrets
- Production: hosting platform secret manager
- Team secret vault: 1Password, Doppler, Infisical, Vault, or equivalent

## Naming

Use explicit environment variable names:

- `OPENAI_API_KEY`
- `DATABASE_URL`
- `SESSION_SECRET`
- `JWT_SIGNING_KEY`

Avoid vague names such as `TOKEN` or `SECRET`.

## Rotation

Rotate a secret immediately if it appears in:

- chat
- terminal history copied to external systems
- logs
- screenshots
- commits or pull requests

## Environment Split

Use different secrets for:

- local development
- staging
- production

Minimum rule: production credentials must never be reused in development.

## Next Step

Once the stack is chosen, add runtime validation for required environment variables in the server application entrypoint.
