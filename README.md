# SafeBallot

Secure and anonymous online voting platform prototype (Django).

This workspace contains a Phase 1 scaffold: Django project, `elections` app, models, crypto utils, and tests.

See `requirements.txt` for dependencies and `.env.example` for required environment variables.

Important: Set `AES_KEY_HEX` in your `.env` to a 64-character hex string (32 bytes) used for AES-256 encryption.
For local testing the test suite sets a temporary key automatically, but in production you must provide a secure key.

Demo stack
----------

To run a local demo with seeded data (admin, two voters, a demo election with two candidates, and two demo votes):

1. Start the stack with the seeder enabled:

```powershell
docker compose up --build -d
docker compose exec web bash -lc "export SEED_DEMO=true; /app/scripts/entrypoint.sh gunicorn safeballot.wsgi:application --bind 0.0.0.0:8000"
```

Or set `SEED_DEMO=true` in `docker-compose.yml` under the `web.environment` section before starting the stack.

2. The demo admin user is `admin` / `AdminPass123`. Two voters were created: `voter1`/`VoterPass1` and `voter2`/`VoterPass2`.

3. The demo election is available on the site index. Results are seeded and the tally can be viewed after the election end time.

Docker / secrets note
---------------------

Do not commit your `.env` file. For local development, copy `.env.example` to `.env` and edit values. The project includes a `.dockerignore` to avoid copying `.env` and local virtualenv into the image.

In production, inject secrets via your host platform or CI (GitHub Actions secrets, AWS Secrets Manager, etc.) rather than baking them into images or `docker-compose.yml`.
