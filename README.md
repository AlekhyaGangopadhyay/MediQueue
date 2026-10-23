# MediQueue: Hospital Appointment and Queue Management System

DBMS mini-project (Healthcare, problem 2). Flask + SQLite, hand-written SQL, live queue dashboard, role-based authentication (Staff/Admin vs Patient Portal).
Full write-up: **[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)**.

## Run it (3 commands)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py --reset && python app.py               # open http://127.0.0.1:5000
```
Run the tests: `python -m unittest discover -s tests -v` (27 tests, no extra packages).

## Default Login Credentials
| Role | Identifier / Username | Password | Access Scope |
|---|---|---|---|
| **Staff / Admin** | `admin` | `admin123` | Full dashboard, all patients, all appointments, live queue calling, reports, history |
| **Patient** | `9831000000` (or self-register) | `patient123` | Personal portal only: my appointments, live queue token & wait time, doctor availability, book/reschedule/cancel own visits, medical history |

## Layout
| File | Purpose |
|---|---|
| `schema.sql` | Tables, constraints, partial unique indexes, triggers, view |
| `db.py` | Connection (foreign keys ON) and the `transaction()` helper |
| `services.py` | Business rules, authentication, booking, queue, audit history |
| `app.py` | Flask routes, role-based access control, CSRF protection, slot API |
| `seed.py` | Demo data (admins, 5 doctors, 15 patients, live queue for today) |
| `templates/`, `static/` | Dashboard, Patient Portal, and Auth UI |
| `tests/test_core.py` | 27 tests for double booking, transactions, queue, security, RBAC |
