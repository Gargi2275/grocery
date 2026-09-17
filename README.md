# Grocery Bill Generator

Full-stack kirana-style bill generator: Django REST + React (Vite) + SQLite.

## What it does

- Single admin login (`ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env`)
- Generates a grocery receipt under a max amount (GST 5% on grocery items, plus small counter adjustments)
- Prints and downloads PDF
- Stores bills in SQLite for reprint from History

## Prerequisites

- Python 3.11+
- Node.js 18+

## Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # already present for local dev
python manage.py migrate
python manage.py runserver
```

API: `http://127.0.0.1:8000`

Default login (from `backend/.env`):

- username: `admin`
- password: `admin123`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

App: `http://localhost:5173` (Vite proxies `/api` to Django)

## Tweak prices / GST

Edit `backend/bills/constants.py`. Grocery pool, adjustment pool, and `GST_RATE` live there — no migration needed.

## API

| Method | Path | Auth |
| --- | --- | --- |
| POST | `/api/login/` | public, returns `{ token }` |
| POST | `/api/generate-bill/` | JWT |
| GET | `/api/bills/` | JWT, paginated |
| GET | `/api/bills/:id/` | JWT |

Generate body:

```json
{
  "shop_name": "Sri Lakshmi Kirana",
  "gst_number": "29ABCDE1234F1Z5",
  "customer_name": "Ramesh",
  "max_amount": "1500.00",
  "date_mode": "fixed",
  "bill_date": "2026-09-17",
  "date_range_start": null,
  "date_range_end": null
}
```

`date_mode`: `fixed` | `monthly` | `random`
# grocery
