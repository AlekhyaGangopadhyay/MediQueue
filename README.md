# 🏥 MediQueue: Hospital Appointment, Queue & Diagnostic Management System

[![Live Demo](https://img.shields.io/badge/Live%20Website-mediqueue--iazh.onrender.com-brightgreen?style=for-the-badge&logo=render)](https://mediqueue-iazh.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3%20(Pure%20SQL)-003B57?style=for-the-badge&logo=sqlite)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Unit%20Tests-29%20Passing-success?style=for-the-badge)](tests/test_core.py)

**MediQueue** is an enterprise-grade, full-stack Hospital Management System (HMS) and Queue Scheduling platform built with **Python, Flask, and pure SQLite3**. Developed as a comprehensive Database Management Systems (DBMS) project, MediQueue places hand-written, rigorous relational database design at the center—enforcing data integrity through foreign keys, check constraints, partial unique indexes, database triggers, and serialized ACID transactions (`BEGIN IMMEDIATE`) rather than relying on heavy ORMs.

The platform is integrated with the complete **`HMS_aiml_22`** healthcare dataset, featuring specialized clinical departments, doctor scheduling, patient medical history, hospital wards/rooms, staff directories, billing/payments, laboratory test results, and a full diagnostic test booking workflow.

---

## 🌐 Live Website & Demo Access

The project is hosted and running publicly on Render:

🔗 **Production URL:** [https://mediqueue-iazh.onrender.com](https://mediqueue-iazh.onrender.com)  
📂 **GitHub Repository:** [https://github.com/AlekhyaGangopadhyay/MediQueue](https://github.com/AlekhyaGangopadhyay/MediQueue)

### Demo Credentials

| Role | Username / Identifier | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Hospital Staff / Admin** | `admin` | `admin123` | Full administrative control: Live queue calling, patient registry, doctor schedules, room allocations, staff directory, billing & payment tracking, lab investigations, and system audit history. |
| **Patient Account** | `9876543210` *(Rahul Sharma)* | `patient123` | Personal Patient Portal: View own queue tokens & live wait time, book/reschedule doctor appointments, view consultation & prescription history, schedule diagnostic tests, and view invoices. |
| **New Patient Self-Registration** | *Any valid 10-digit phone* | *Self-chosen* | Patients can register instantly at `/register` to create a personal portal account. |

---

## 🚀 Key Modules & System Features

### 1. 🔐 Role-Based Access Control (RBAC) & Authentication
* **Isolated Portals**: Dynamic interface tailored for **Hospital Staff (Admin)** vs. **Patients**.
* **Security**: Salted password hashing with `werkzeug.security` (PBKDF2 SHA-256), session cookie integrity, and cryptographic CSRF tokens on every form state change.
* **Patient Data Isolation**: Patients are strictly sandboxed—they can only access and modify their own appointments, records, and bookings.

### 2. 📅 Doctor Scheduling & Zero Double-Booking Guarantee
* **Weekly Schedule Matrix**: Configurable consultation slots (10, 15, 20 mins) per doctor based on working days and shifts.
* **Mathematical Double-Booking Prevention**: Enforced at the database engine level using SQLite partial unique indexes (`uq_doctor_slot_live` and `uq_patient_slot_live`) combined with `BEGIN IMMEDIATE` concurrency write-locks.

### 3. ⏱️ Real-Time Queue & Waiting Time Estimation
* **Token Issuance**: Check-in on appointment day generates a sequential daily token per doctor.
* **Dynamic Wait Calculation**: Evaluated via SQL view `v_queue`, calculating `people_ahead` and `est_wait_min = people_ahead * consult_minutes`.
* **Live Calling Dashboard**: Staff calls patients into consultation (`CALLED`), completes with diagnosis/prescription (`COMPLETED`), or marks no-shows (`SKIPPED`). The live board polls asynchronously without full page refreshes.

### 4. 🔬 Laboratory & Diagnostic Test Booking
* **Tariff Catalog**: 10 standard pathology and radiology investigations (e.g., Fasting Blood Sugar, CBC, Lipid Profile, ECG, CT Scan Abdomen, MRI Brain with Contrast, X-Ray Chest).
* **Self-Service Booking**: Patients can schedule diagnostic appointments with custom date and time slots (`07:30`, `08:30`, `09:30`, etc.).
* **Pre-Investigation Guidance**: Built-in fasting instructions and sample collection guidelines.
* **Results & Audit**: Staff can mark tests as completed, while patients track upcoming lab bookings directly inside their portal.

### 5. 🏥 Complete Hospital Operations (`HMS_aiml_22` Integration)
* **Wards & Rooms**: Tracks room numbers, floor levels, bed types (General, Private, ICU), and occupancy statuses.
* **Staff Directory**: Medical and administrative staff records (Nurses, Lab Technicians, Pharmacists, Ward Admins).
* **Billing & Invoices**: Invoice generation, partial/full payment logging (Cash, Card, UPI), and transaction reconciliation.
* **Medical Consultations**: Historical diagnosis, doctor treatment plans, prescription notes, and physician notes.

### 6. 📜 Immutable Audit History (Append-Only Triggers)
* Automated audit trail tracking all appointment state transitions (`BOOKED` → `CHECKED_IN` → `IN_CONSULTATION` → `COMPLETED` / `RESCHEDULED` / `CANCELLED`).
* Enforced with `BEFORE UPDATE` and `BEFORE DELETE` database triggers raising `ABORT` errors on tamper attempts.

---

## 🗄️ Relational Database Architecture

```mermaid
erDiagram
    DEPARTMENTS ||--o{ DOCTORS : employs
    DEPARTMENTS ||--o{ ROOMS : allocates
    ROOMS ||--o{ STAFF : assigned_to
    DOCTORS ||--o{ DOCTOR_SCHEDULES : works
    DOCTORS ||--o{ APPOINTMENTS : attends
    PATIENTS ||--o{ APPOINTMENTS : books
    PATIENTS ||--o{ BILLS : billed_to
    BILLS ||--o{ PAYMENTS : settles
    PATIENTS ||--o{ TEST_BOOKINGS : schedules
    TESTS ||--o{ TEST_BOOKINGS : contains
    PATIENTS ||--o{ TEST_RESULTS : undergoes
    TESTS ||--o{ TEST_RESULTS : categorizes
    APPOINTMENTS ||--o| QUEUE_TOKENS : "issues token"
    APPOINTMENTS ||--o| CONSULTATIONS : "results in"
    APPOINTMENTS ||--o{ APPOINTMENT_HISTORY : "audits"
    
    DEPARTMENTS { int dept_id PK  string name UK  string location  string phone }
    DOCTORS { int doctor_id PK  string full_name  int dept_id FK  string specialization  string phone UK  int consult_minutes }
    DOCTOR_SCHEDULES { int schedule_id PK  int doctor_id FK  int weekday  string start_time  string end_time }
    PATIENTS { int patient_id PK  string full_name  string date_of_birth  string gender  string phone UK  string blood_group }
    ROOMS { int room_id PK  string room_no UK  string room_type  int floor  string status  real daily_charge }
    STAFF { int staff_id PK  string full_name  string role  string phone  int room_id FK }
    APPOINTMENTS { int appointment_id PK  int patient_id FK  int doctor_id FK  string appt_date  string slot_time  string status }
    QUEUE_TOKENS { int token_id PK  int appointment_id FK_UK  int doctor_id FK  int token_no  string status }
    CONSULTATIONS { int consultation_id PK  int appointment_id FK_UK  string diagnosis  string prescription  string treatment }
    TESTS { int test_id PK  string test_name  string test_type  real cost }
    TEST_BOOKINGS { int booking_id PK  int test_id FK  int patient_id FK  string booking_date  string slot_time  string status }
    TEST_RESULTS { int result_id PK  int test_id FK  int patient_id FK  string result_value  string unit  string normal_range }
    BILLS { int bill_id PK  int patient_id FK  string bill_date  real total_amount  real amount_paid  string payment_status }
    PAYMENTS { int payment_id PK  int bill_id FK  real amount  string payment_mode  string transaction_no }
    APPOINTMENT_HISTORY { int history_id PK  int appointment_id FK  string action  string old_status  string new_status }
```

---

## 🛠️ Technology Stack

* **Backend**: Python 3.10+, Flask 3.0+
* **WSGI Production Server**: Gunicorn
* **Database**: SQLite3 with Hand-Written SQL (Foreign Keys enabled, WAL journal mode)
* **Frontend**: Vanilla HTML5, CSS3, modern Vanilla JavaScript (no bloat, highly responsive design)
* **Deployment & Cloud**: Render Web Service (Cloudflare SSL, Auto-Deploy via GitHub CI/CD)

---

## 💻 Local Setup & Installation

### 1. Clone Repository
```bash
git clone https://github.com/AlekhyaGangopadhyay/MediQueue.git
cd MediQueue
```

### 2. Create and Activate Virtual Environment
```bash
# On Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# On Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database with HMS Dataset
```bash
python seed.py --reset
```
*This resets and automatically seeds all 10 departments, 10 doctors with working schedules, 10 rooms, 10 staff, 10 patients, lab tests, invoices, and live queue demonstrations.*

### 5. Start Application Server
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.

---

## 🧪 Automated Testing Suite

The repository includes a comprehensive unit testing suite covering booking validation, concurrency collision handling, trigger append-only audit enforcement, queue position arithmetic, RBAC isolation, CSRF protection, and diagnostic booking flows:

```bash
python -m unittest discover -s tests -v
```

**Results:**
```text
Ran 29 tests in 3.484s

OK
```

---

## 📁 Repository Directory Structure

```text
Hospital_DBMS/hospital_queue/
├── app.py                      # Flask application factory, routing & RBAC middleware
├── db.py                       # Connection helpers, schema migrations & transaction context
├── schema.sql                  # Canonical DDL: tables, indexes, triggers & queue views
├── seed.py                     # Realistic dataset seeding from HMS_aiml_22
├── services.py                 # Pure SQL business logic layer (ACID transactions)
├── Procfile                    # Render production process specification
├── requirements.txt            # Python dependencies (Flask, Gunicorn)
├── static/
│   ├── css/
│   │   └── style.css           # Modern clinical design system & responsive UI
│   └── js/
│       └── app.js              # Live queue polling & interactive slot picker
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Shared layout & navigation sidebar
│   ├── login.html              # Multi-role authentication interface
│   ├── register.html           # Patient self-registration portal
│   ├── dashboard.html          # Staff executive overview & KPI metrics
│   ├── queue.html              # Real-time queue calling board
│   ├── appointments.html       # Appointment master directory
│   ├── book.html               # Doctor appointment booking wizard
│   ├── patient_portal.html     # Patient self-service portal
│   ├── tests.html              # Diagnostic investigation catalog & bookings
│   ├── test_book.html          # Laboratory test appointment scheduler
│   ├── billing.html            # Invoicing and payment history
│   ├── rooms.html              # Ward and room occupancy matrix
│   ├── staff.html              # Hospital employee directory
│   └── 500.html                # Graceful error recovery page
└── tests/
    └── test_core.py            # 29 automated test cases
```

---

## 📄 License & Attribution

Distributed under the MIT License. Developed for Academic Database Management Systems (DBMS) project evaluation.
Live deployment: [https://mediqueue-iazh.onrender.com](https://mediqueue-iazh.onrender.com)
