# REFOOD

Hackathon application for pantry scanning, recipe recommendations, and food-budget planning.

See [backend setup](src/backend/README.md) and [developer notes](docs/obsidian/Backend%20Architecture.md).


## Backend MVP (MariaDB + Flask)

For Linux/Fedora setup, copied example credentials, a repeatable Docker Compose command (including sudo), database initialization, demo seeding and tests, see [MVP Local Setup](docs/obsidian/MVP%20Local%20Setup.md).

Quick database start from the repository root, after copying `src/backend/database/.env.example` to `src/backend/database/.env`:

```bash
sudo docker compose --env-file src/backend/database/.env -f src/backend/database/compose.yaml up -d --wait
```

The credentials in the template are only suitable for local development. The frontend is not yet wired to the real Flask backend; see the setup note for remaining MVP gaps.
