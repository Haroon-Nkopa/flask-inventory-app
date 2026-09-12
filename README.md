# StockWise

StockWise is a production-oriented Flask application deployed on Render and backed by PostgreSQL hosted on Neon. This repository is organized as a maintainable web service: application creation is separated from the WSGI entry point, persistence is managed through SQLAlchemy and Alembic, access control is enforced at the route boundary, and database-backed workflows have automated tests.

Live deployment: https://flask-inventory-app-52kj.onrender.com

## Engineering overview

### Application architecture

- `app.create_app()` is the application factory. It initializes extensions, authentication, error handlers, logging, and blueprints without coupling them to a single process startup path.
- Flask blueprints separate authentication, administration, subscriptions, and the main operational API/UI.
- SQLAlchemy models define the relational domain. Flask-Migrate and Alembic provide versioned schema changes in `migrations/`.
- Jinja templates provide server-rendered pages, while JavaScript modules consume focused JSON endpoints for interactive workflows.
- `entryPoint.py` exposes the factory-created application as `app` for Gunicorn and local execution.

### Data and consistency

Production data is stored in a managed Neon PostgreSQL database. Render supplies the connection through `DATABASE_URL`; the configuration normalizes legacy `postgres://` URLs and applies connection pool recycling for a long-running web process. PostgreSQL connection strings should include the SSL settings supplied by Neon.

The schema represents shops, users, products, live inventory, sales, sale items, daily snapshots, physical counts, audit merges, and cashless transactions. Shop scoping and role/payment decorators are applied before protected handlers execute. Inventory-changing operations validate ownership and availability and persist related records through the SQLAlchemy session.

SQLite remains available as a local fallback and is used by the test fixtures for isolated, disposable databases. It is not a production data store for the deployed service.

### Operational concerns

- Production runs behind Gunicorn on Render.
- Non-debug application logs use a rotating file handler with ten retained files.
- The global 500 handler rolls back the current database session before rendering the error page.
- Migrations are applied explicitly with `flask db upgrade`; schema changes should not be introduced by calling `db.create_all()` in production.
- Secrets and database credentials are supplied through environment variables and must not be committed to the repository.

## Technology stack

- **Runtime:** Python, Flask, Gunicorn
- **Persistence:** PostgreSQL on Neon, SQLAlchemy, Flask-SQLAlchemy
- **Schema management:** Flask-Migrate and Alembic
- **Authentication:** Flask-Login and Werkzeug password hashing
- **Presentation:** Jinja, HTML, CSS, JavaScript, and Bootstrap
- **Document generation:** ReportLab
- **Hosting:** Render
- **Testing:** pytest, Flask test client, and isolated SQLite fixtures

## Local development

### Prerequisites

- Python 3.8 or newer
- `pip` and Git
- A PostgreSQL-compatible `DATABASE_URL` for testing against a shared development database, or use the local SQLite fallback

### Setup

```bash
git clone https://github.com/Haroon-Nkopa/flask-inventory-app.git
cd flask-inventory-app

python -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
pip install pytest
export SECRET_KEY="replace-with-a-random-secret"
```

For local development, `DATABASE_URL` may be omitted and the application will use `app.db`. To connect to Neon or another PostgreSQL instance, set the provider's complete connection string:

```bash
export DATABASE_URL="postgresql://user:password@host/database?sslmode=require"
```

Apply the current schema and start the service:

```bash
flask db upgrade
python entryPoint.py
```

The development server listens on `http://localhost:5000`. Sample data can be loaded with `python seed_data.py` when working against an intentionally disposable database.

## Tests

The repository includes pytest coverage for application routes. Fixtures create and destroy an isolated in-memory SQLite database per test, seed only the records needed by the scenario, and exercise the Flask test client with authentication and shop-session state.

Run the test suite with:

```bash
python -m pytest app/main/tests
```

Tests do not use the production Neon database. This keeps test execution deterministic and prevents test data from reaching shared environments.

## Database migrations

When a model changes, generate and review a migration, then apply it to the target environment:

```bash
flask db migrate -m "Describe the schema change"
flask db upgrade
```

Commit the generated migration with the model change. In deployment, run `flask db upgrade` before serving code that depends on the new schema.

## Deployment

The live service uses the following Render configuration:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn entryPoint:app`
- **Required environment variables:** `SECRET_KEY` and the Neon `DATABASE_URL`

Deployment sequence:

1. Install the pinned Python dependencies.
2. Apply Alembic migrations with `flask db upgrade`.
3. Start Gunicorn with `entryPoint:app`.
4. Inspect Render logs if startup, migration, or database connectivity fails.

Do not rely on a local SQLite file in Render's ephemeral filesystem for durable data.

## Repository layout

```text
flask-inventory-app/
├── app/
│   ├── __init__.py             # Application factory and extension setup
│   ├── models.py               # SQLAlchemy models and relationships
│   ├── decorators.py           # Shop, role, and payment authorization
│   ├── main/                   # Core routes, APIs, helpers, and tests
│   ├── auth/                   # Authentication routes
│   ├── admin/                  # Administrative routes
│   ├── subscription/           # Subscription routes
│   ├── templates/              # Jinja templates
│   ├── static/                 # Browser assets and service worker
│   └── utils/                  # PDF generation utilities
├── migrations/                 # Alembic migration history
├── config.py                   # Environment-backed configuration
├── entryPoint.py               # WSGI entry point and shell context
├── requirements.txt            # Runtime dependencies
├── seed_data.py                # Optional development data loader
└── README.md
```

## Contributing

Keep changes scoped to the relevant blueprint, model, migration, or frontend module. For persistence changes, include the migration and update the affected tests. Before opening a pull request, run the test suite, review generated migrations, and verify that secrets and production connection strings are not present in the diff.
