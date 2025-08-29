## SafeBallot

Secure and anonymous online voting platform — prototype built with Django. This repository contains a Phase‑1 implementation with an `elections` app, AES‑GCM vote encryption utilities, basic UI, a seeder, and unit tests.

This README explains how to run the project locally, use the demo seeder, manage secrets, run tests, and prepare for production.

## Quick links

- Project: Django (Python 3.11+)
- App: `elections`
- Crypto: AES‑GCM using an environment key `AES_KEY_HEX` (32 bytes in hex, 64 chars)
- Docker: `docker-compose.yml` included for local demo

## Prerequisites

- Python 3.11+ (if running without Docker)
- Docker & Docker Compose (for containerized local demo)
- Git (recommended)

## Environment variables

Copy the example and edit values for your environment:

```powershell
copy .env.example .env
# then edit .env in your editor
```

Important variables:

- `AES_KEY_HEX` — Required for encryption. Must be a 64-character hex string (32 bytes). Changing this value in production will prevent decryption of existing votes.
- `DJANGO_SECRET_KEY` — Django secret key (do not use the dev default in production).
- `DATABASE_PASSWORD` — Database password if using external DB.

Never commit your `.env` to source control. `.gitignore` already contains `.env` and other local artifacts.

## Run locally (no Docker)

1. Create a venv and install dependencies:

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    ```

2. Populate `.env` (see above). Then run migrations and start the dev server:

    ```powershell
    python manage.py migrate
    python manage.py runserver
    ```

3. Optionally seed demo data (creates an admin and sample voters):

    ```powershell
    python manage.py seed_demo
    ```

The site will be available at http://127.0.0.1:8000/.

## Run with Docker (recommended for quick demos)

The repository includes a `docker-compose.yml` that starts a web service and a Postgres database for local development.

To run the demo (PowerShell):

```powershell
docker compose up --build -d
```

If you want the demo seeder to run inside the container, set the `SEED_DEMO` environment variable in your `.env` or in `docker-compose.yml` under the `web.environment` section. Example (in `.env`):

```text
SEED_DEMO=true
```

To view logs or run a shell in the web container:

```powershell
docker compose logs -f web
docker compose exec web bash
```

Notes:

- The compose file currently includes development/demo credentials (`safeballot_pass`) for convenience. Do not use these values in production. Replace them with secure values stored outside the repository (or provide them via `.env`, which must remain gitignored).
- The `Dockerfile` is a multi-stage build and runs the app as a non-root user to improve image hygiene.

## Demo credentials (local/test only)

- Admin: `admin` / `AdminPass123`
- Voters: `voter1`/`VoterPass1`, `voter2`/`VoterPass2`

These are seeded only if you enable the seeder. Do not use them in production.

## AES key and data stability

The application encrypts votes using AES‑GCM with the key supplied by `AES_KEY_HEX`. This key is critical:

- It must be 64 hex characters (32 bytes).
- If you change the key in production, previously encrypted votes will no longer be decryptable. Treat this as a non-rotatable key for stored ballots unless you implement key wrapping or re-encryption.

## CI / GitHub Actions

CI is configured to require `AES_KEY_HEX` as a repository secret. Before enabling CI on your repository, add the secret in GitHub: Settings → Secrets → Actions → New repository secret, name it `AES_KEY_HEX` and paste the 64-character hex key.

The workflow intentionally fails if `AES_KEY_HEX` is absent to avoid running tests with a demo key.

## Tests

Run the Django test suite locally:

```powershell
python manage.py test
```

Unit tests set a demo AES key at runtime so they can run in CI and local dev. This demo key is for tests only and must not be used for production data.

## Production recommendations (summary)

- Use a managed secrets store (GitHub Secrets, AWS Secrets Manager, HashiCorp Vault) to provide `AES_KEY_HEX`, `DJANGO_SECRET_KEY`, and DB credentials.
- Use PostgreSQL or another production-grade RDBMS (the compose file can be adapted to use a hosted DB).
- Serve static files from a CDN or object storage (S3/MinIO) and protect media uploads.
- Put the application behind an HTTPS reverse proxy (Nginx, Traefik) and terminate TLS there.
- Add monitoring, structured logging, and backup/restore for the encrypted ballots. Plan key management carefully.

## Troubleshooting

- If you see AES key errors, ensure `AES_KEY_HEX` is set and valid (64 hex characters). The app will raise a RuntimeError if the key is missing or invalid.
- If migrations fail, ensure your DB credentials in `.env` match the running database.

## Contributing

Contributions are welcome. For small fixes, send a PR. For major changes (key management, production deployment), open an issue first to discuss design and security implications.

## Licenses

This repository is licensed under the MIT License. See the `LICENSE` file at the repository root for the full text.

Third-party license inventory

- A companion file `THIRD_PARTY_LICENSES.md` lists the common third-party components and how to produce a precise bill-of-materials. For Python packages, a reproducible way to capture installed package licenses is:

```powershell
pip install pip-licenses
pip-licenses --format=columns > THIRD_PARTY_PYTHON_LICENSES.txt
```

Verify frontend libraries (Bootstrap, Chart.js, Feather icons, etc.) by checking their LICENSE files in the packages or upstream repositories.

If you want me to populate `THIRD_PARTY_PYTHON_LICENSES.txt` for this repo (using the project's `requirements.txt`), I can run `pip-licenses` in a venv, capture the output, and commit the result.

## Contact

If you want help with deployment hardening, secret rotation, or an audit of the repository history for leaked secrets, say the word and I can run the checks or apply the proposed changes.
