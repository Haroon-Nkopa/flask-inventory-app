# StockWise

StockWise is a Flask web application for managing inventory, point-of-sale transactions, physical stock counts, and shop-level reporting. It is designed for retail businesses that need live stock balances, staff permissions, and an audit trail for inventory changes.

## Live application

The application is hosted on Render:

**https://flask-inventory-app-52kj.onrender.com**

## Features

### Shop and account management

- Select a shop before entering the workspace.
- Authenticate users with password-protected accounts and Flask-Login sessions.
- Support the roles `owner`, `manager`, `employee`, `auditor`, and system `admin`.
- Restrict shop data and actions according to the active shop and the user role.
- Allow owners and managers to open the add-user screen for shop staff.

### Product and inventory management

- Add products with a name, category, size, selling price, batch size, batch price, reorder lower bound, and batch number.
- Edit product details while preventing duplicate names within a shop.
- Receive new stock and update the live inventory balance.
- View live stock, daily inventory snapshots, and physical audit records.
- Perform one physical stock take per shop per day, with global or product-specific notes.
- Record the user responsible for each physical count.
- Download a printable PDF stock sheet for the active shop.

### Point of sale

- Browse products and their current live quantities in the POS screen.
- Build a cart and complete a sale after validating product ownership and available stock.
- Consolidate duplicate cart lines before checkout.
- Deduct sold quantities from live inventory and create sale and sale-item records atomically.
- Record cashless stock allocations as `personal`, `stoloto`, or `other`, with an explanation required for `other`.

### Reporting and audit

- Browse paginated sales history with product, quantity, price, total, and timestamp details.
- View an owner-only live summary containing today's revenue, potential profit, stock-outs, fast-selling products, top-earning products, and a seven-day revenue chart.
- Compare historical daily stock counts over a selected date range.
- Review audited physical-count logs from the last 30 days or a selected range.
- Compare live and audited quantities to identify inventory discrepancies.
- Merge a verified variance into inventory with a required reason.

## Technology

- **Backend:** Python and Flask
- **Database and ORM:** SQLAlchemy with Flask-Migrate/Alembic
- **Authentication:** Flask-Login and Werkzeug password hashing
- **Frontend:** Jinja templates, HTML, CSS, JavaScript, and Bootstrap
- **Charts:** Chart.js assets used by the summary views
- **Documents:** ReportLab PDF stock-sheet generation
- **Production hosting:** Render
- **Application server:** A WSGI server such as Gunicorn can serve `entryPoint:app`

## Run locally

### Requirements

- Python 3.8 or newer
- `pip`
- Git

### Setup

```bash
git clone https://github.com/Haroon-Nkopa/flask-inventory-app.git
cd flask-inventory-app

python -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate      # Windows

pip install -r requirements.txt
```

Configure the application with environment variables. The default database is a local SQLite file named `app.db` in the project root.

```bash
export SECRET_KEY="replace-with-a-random-secret"
# Optional: use a managed database instead of local SQLite
export DATABASE_URL="sqlite:///app.db"
```

Apply migrations and start the development server:

```bash
flask db upgrade
python entryPoint.py
```

Open `http://localhost:5000` in a browser.

To load the repository's sample data, run:

```bash
python seed_data.py
```

## Render deployment

The live service runs on Render. A typical Render web service configuration is:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn entryPoint:app`
- **Environment variables:** set a strong `SECRET_KEY` and a production `DATABASE_URL`.

Run database migrations as part of the deployment process before using schema changes:

```bash
flask db upgrade
```

For production, use a managed database or persistent storage. A local SQLite file in a web service's ephemeral filesystem should not be treated as durable production data. Render provides HTTPS for the deployed service, so the application no longer requires an EC2 or self-signed-certificate setup.

## Main application routes

The main blueprint serves the following workflows. Most screens load their data through the accompanying `/api/...` endpoints.

| Route | Purpose | Access |
| --- | --- | --- |
| `/` | Select the active shop | Public entry point |
| `/shop` | Shop product workspace | Authenticated shop users |
| `/add` | Add-product screen | Owner, manager, employee |
| `/edit-product` | Edit-product screen | Owner, manager, employee |
| `/new-stocks` | Receive stock screen | Authenticated shop users |
| `/take-stock` | Physical stock-take screen | Owner, manager, employee, auditor |
| `/stock-history` | Live, daily, and audited stock history | Owner, manager |
| `/pos` | Point-of-sale screen | Owner, manager, employee, auditor |
| `/sales-history` | Paginated sales history | Owner, manager, auditor |
| `/summary` | Revenue, stock, sales, and audit summary | Owner |
| `/print-stock-sheet` | Download a PDF stock sheet | Authenticated shop users |
| `/logout` | End the current session | Authenticated users |

Important JSON endpoints include:

- `/api/products` and `/api/products/<product_id>` for creating and updating products.
- `/api/new-stocks` for receiving stock.
- `/api/take-stock` and `/api/stock-take-products` for physical counts.
- `/api/pos/products`, `/api/pos/checkout`, and `/api/pos/cashless` for POS operations.
- `/api/sales-history` for paginated transaction history.
- `/api/summary/live`, `/api/summary/daily-count`, and `/api/summary/audited` for reporting data.
- `/api/inventory/discrepancies` and `/api/inventory/merge-variance` for variance review and reconciliation.

## Project structure

```text
flask-inventory-app/
├── app/
│   ├── __init__.py             # Flask app factory and blueprint registration
│   ├── models.py               # SQLAlchemy models
│   ├── decorators.py           # Shop, role, and payment access checks
│   ├── main/                   # Inventory, POS, audit, and reporting workflows
│   ├── auth/                   # User login and logout
│   ├── admin/                  # System admin shop and user management
│   ├── subscription/           # Shop registration and subscription screens
│   ├── templates/               # Jinja HTML templates
│   ├── static/                  # CSS, JavaScript, manifest, and service worker assets
│   └── utils/                   # PDF stock-sheet generation
├── migrations/                 # Alembic migration history
├── config.py                   # Environment-backed Flask configuration
├── entryPoint.py               # WSGI application entry point
├── requirements.txt            # Python dependencies
├── seed_data.py                # Optional sample-data loader
└── README.md
```

## Database model areas

The data model includes shops and users, products, live inventory, sales and sale items, daily inventory snapshots, physical inventory counts, inventory records, and cashless transactions. Inventory queries are scoped to the active shop, while role and payment decorators protect sensitive screens and APIs.

## Development notes

Apply migrations after changing models:

```bash
flask db migrate -m "Describe the schema change"
flask db upgrade
```

There is currently no committed test suite in the repository. Before deploying changes, verify the affected workflow locally and check the Render service logs for migration or database errors.

## License and support

For questions, bug reports, or feature requests, open an issue in the GitHub repository:

https://github.com/Haroon-Nkopa/flask-inventory-app