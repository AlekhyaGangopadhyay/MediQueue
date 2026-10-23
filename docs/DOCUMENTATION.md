# MediQueue: Hospital Appointment and Queue Management System

**Course:** Database Management Systems, mini-project (Problem 2, Healthcare)
**Stack:** Python 3.10+, Flask, SQLite (plain SQL via `sqlite3`), HTML/CSS/JavaScript

---

## 1. Problem and aim

Patients lose hours waiting for consultations because appointments and walk-in queues are managed on paper or
in disconnected tools. Two things go wrong: **the same doctor slot gets given to two people**, and **nobody knows
how long the wait will be**.

**Aim:** build a database-driven system that
1. registers patients and doctors,
2. books, reschedules and cancels appointments **without ever double-booking**,
3. issues queue tokens at check-in and shows each patient's **position and estimated wait**,
4. keeps a permanent **appointment history** and **consultation history**,
5. shows the current queue on a live **dashboard**.

The emphasis is on database design. Every integrity rule is enforced **inside the database**
(keys, constraints, unique indexes, triggers, transactions), and the Flask code on top only adds friendly messages.

## 2. Requirement to implementation map

| Assignment requirement | Where it is implemented |
|---|---|
| Register patients and doctors | `patients`, `doctors`, `doctor_schedules` tables; `/patients/new`, `/doctors/new` |
| Patient and Admin Authentication | `admins` table, `patients.password_hash`, Werkzeug password hashing; `/login`, `/register`, `/logout` |
| Patient Portal & Isolation | `/portal`, patient can only see & manage own appointments and view doctor availability |
| Book, reschedule, cancel | `book_appointment`, `reschedule_appointment`, `cancel_appointment` in `services.py` |
| Queue tokens + estimated waiting position | `queue_tokens` table, `v_queue` view (`people_ahead`, `est_wait_min`), `check_in()` |
| Consultation and appointment history | `consultations` table, `appointment_history` table filled by triggers |
| Relationships, foreign keys | 8 tables linked by FKs (section 4) |
| Transactions | `db.transaction()` (`BEGIN IMMEDIATE`) wraps every multi-step change |
| Unique constraints | `phone`, `email`, `(doctor_id, weekday)`, `(doctor_id, queue_date, token_no)`, partial unique indexes |
| Joins | patient history (4-table join), queue view (4-table join), dashboard reports |
| Prevention of double booking | Partial unique indexes + pre-checks inside a transaction (section 6) |
| Flask + queue dashboard | `app.py`, `templates/queue.html` (auto-refreshes every 10 s) |

## 3. System overview

```
Browser (HTML/CSS/JS)  ->  Flask routes (app.py)  ->  services.py (rules)  ->  SQLite (schema.sql)
        ^ polls /queue/partial every 10 s                      BEGIN IMMEDIATE ... COMMIT
```

**Typical day**
1. Reception registers a patient and books a slot with a doctor (the slot list comes from the doctor's weekly hours and
   consultation length; taken slots are greyed out).
2. On the day, the patient arrives and is **checked in**. The system issues the next token number for that doctor.
3. The doctor presses **Call next**. The lowest waiting token becomes *Now serving* and a consultation record starts.
4. The doctor saves diagnosis and prescription with **Save and complete**. The token and appointment close.
5. Every other waiting patient's position and estimated wait update immediately.

**Appointment status life cycle**

```
BOOKED --check-in--> CHECKED_IN --call next--> IN_CONSULTATION --complete--> COMPLETED
  |                      |  \--skip--> NO_SHOW
  \-----cancel-----------/--cancel--> CANCELLED          (BOOKED can also be rescheduled)
```
`CANCELLED` and `NO_SHOW` free the slot so it can be booked again.

## 4. Database design

### 4.1 ER diagram

```mermaid
erDiagram
    DEPARTMENTS ||--o{ DOCTORS : employs
    DOCTORS ||--o{ DOCTOR_SCHEDULES : works
    DOCTORS ||--o{ APPOINTMENTS : receives
    PATIENTS ||--o{ APPOINTMENTS : books
    APPOINTMENTS ||--o| QUEUE_TOKENS : "gets at check-in"
    APPOINTMENTS ||--o| CONSULTATIONS : "results in"
    APPOINTMENTS ||--o{ APPOINTMENT_HISTORY : "audited by"
    DOCTORS ||--o{ QUEUE_TOKENS : serves
    DEPARTMENTS { int dept_id PK  text name UK }
    DOCTORS { int doctor_id PK  text full_name  int dept_id FK  text phone UK  text email UK  int consult_minutes  int is_active }
    DOCTOR_SCHEDULES { int schedule_id PK  int doctor_id FK  int weekday  text start_time  text end_time }
    PATIENTS { int patient_id PK  text full_name  text date_of_birth  text gender  text phone UK  text email UK }
    APPOINTMENTS { int appointment_id PK  int patient_id FK  int doctor_id FK  text appt_date  text slot_time  text status }
    QUEUE_TOKENS { int token_id PK  int appointment_id FK_UK  int doctor_id FK  text queue_date  int token_no  text status }
    CONSULTATIONS { int consultation_id PK  int appointment_id FK_UK  text started_at  text ended_at  text diagnosis  text prescription }
    APPOINTMENT_HISTORY { int history_id PK  int appointment_id FK  text action  text old_status  text new_status }
```

### 4.2 Tables

| Table | Purpose | Key constraints |
|---|---|---|
| `admins` | Hospital administrator accounts | `username` UNIQUE; Werkzeug password hash |
| `departments` | Reference list | `name` UNIQUE |
| `doctors` | Doctor profile and slot length | FK `dept_id`; UNIQUE `phone`, `email`; CHECK `consult_minutes` 5-120 |
| `doctor_schedules` | Weekly working hours | FK `doctor_id` (cascade); UNIQUE `(doctor_id, weekday)`; CHECK `start_time < end_time` |
| `patients` | Patient profile & credentials | UNIQUE `phone`, `email`; CHECK gender in M/F/O; `password_hash` |
| `appointments` | One booking | FKs to patient and doctor (RESTRICT); CHECK status; two partial unique indexes |
| `queue_tokens` | Token issued at check-in | UNIQUE `appointment_id`; UNIQUE `(doctor_id, queue_date, token_no)`; partial unique index (one `CALLED`) |
| `consultations` | Visit notes | UNIQUE `appointment_id` (1:1) |
| `appointment_history` | Audit trail | Filled by triggers; update and delete blocked by triggers |

### 4.3 Normalization
All tables are in **3NF**: every non-key attribute depends on the key, the whole key, and nothing but the key.
Department names live in `departments` (not repeated per doctor). Patient and doctor details live once and are
referenced by id. `queue_tokens.doctor_id` and `queue_date` are copied from the appointment **on purpose**: they are needed to
make `(doctor_id, queue_date, token_no)` unique, and they are written together with the appointment id inside one
transaction, so they cannot disagree. Dates and times are stored as ISO text (`YYYY-MM-DD`, `HH:MM`), which sorts correctly.

### 4.4 Referential actions
Appointments, tokens, consultations and history use `ON DELETE RESTRICT`: a patient or doctor who has records
cannot be deleted, which protects medical history. Only `doctor_schedules` cascades when a doctor is removed.

## 5. Queue logic

* **Token number:** `MAX(token_no) + 1` for that doctor and day, computed inside the check-in transaction.
  Numbers restart each day and are independent per doctor.
* **Position / wait** (view `v_queue`):
  `people_ahead` = tokens of the same doctor and day with a smaller number that are `WAITING` or `CALLED`;
  `est_wait_min = people_ahead x consult_minutes`. Position is `people_ahead + 1`.
  The patient currently in consultation counts as one full consultation, which is a conservative estimate.
  Cancelled, skipped and finished tokens drop out, so the wait shrinks automatically.
* **One patient at a time:** a partial unique index allows at most one `CALLED` token per doctor per day.

## 6. Preventing double booking (the core DBMS idea)

Three layers, strongest last:

1. **Slot generation.** The UI only offers free slots, taken from the doctor's schedule minus live appointments.
2. **Transactional pre-check.** `book_appointment` runs in `BEGIN IMMEDIATE`, which takes the database write lock first.
   Two simultaneous requests are therefore serialised: the second sees the first one's row and gets a clear message.
3. **Database constraint (final guarantee).**
   ```sql
   CREATE UNIQUE INDEX uq_doctor_slot_live  ON appointments (doctor_id,  appt_date, slot_time)
       WHERE status NOT IN ('CANCELLED','NO_SHOW');
   CREATE UNIQUE INDEX uq_patient_slot_live ON appointments (patient_id, appt_date, slot_time)
       WHERE status NOT IN ('CANCELLED','NO_SHOW');
   ```
   Even a bug in the application, or a manual `INSERT`, cannot create a duplicate. The `WHERE` makes the index
   *partial*, so a cancelled slot becomes bookable again while history rows are kept.

This is verified by tests, including four threads racing for one slot (exactly one wins) and a raw SQL insert
that the database rejects.

## 7. Transactions used

| Operation | Steps that must succeed together |
|---|---|
| Book | validate -> insert appointment (-> trigger writes history) |
| Reschedule | validate new slot (ignoring own row) -> update date/time (-> trigger) |
| Cancel | set appointment `CANCELLED` -> set waiting token `CANCELLED` |
| Check-in | compute next token -> insert token -> set `CHECKED_IN` |
| Call next | confirm nobody `CALLED` -> mark token `CALLED` -> appointment `IN_CONSULTATION` -> insert consultation |
| Complete | token `DONE` -> appointment `COMPLETED` -> fill consultation notes |
| Skip | token `SKIPPED` -> appointment `NO_SHOW` |

`db.transaction()` issues `COMMIT` on success and `ROLLBACK` on any exception, so no operation can leave
half-written data (tested in `test_failed_booking_leaves_no_partial_data`).

## 8. Triggers and view
* `trg_appt_created` / `trg_appt_changed` write a row to `appointment_history` for every booking, reschedule, check-in,
  cancellation and status change, with old and new values.
* `trg_history_no_update` / `trg_history_no_delete` make the log append-only (`RAISE(ABORT)`).
* `v_queue` joins `queue_tokens`, `appointments`, `patients` and `doctors` and computes position and wait.

## 9. Useful SQL (all tested on the demo data)

```sql
-- Today's appointments with patient, doctor and department (4-table join)
SELECT a.slot_time, p.full_name AS patient, d.full_name AS doctor, dep.name AS department, a.status
FROM appointments a
JOIN patients p ON p.patient_id = a.patient_id
JOIN doctors d ON d.doctor_id = a.doctor_id
JOIN departments dep ON dep.dept_id = d.dept_id
WHERE a.appt_date = date('now','localtime') ORDER BY a.slot_time;

-- Doctor workload today (LEFT JOIN + GROUP BY)
SELECT d.full_name, COUNT(a.appointment_id) AS total, SUM(a.status = 'COMPLETED') AS done
FROM doctors d LEFT JOIN appointments a
  ON a.doctor_id = d.doctor_id AND a.appt_date = date('now','localtime')
GROUP BY d.doctor_id ORDER BY total DESC;

-- Doctors free at 10:00 tomorrow (NOT EXISTS)
SELECT d.full_name FROM doctors d WHERE NOT EXISTS (
  SELECT 1 FROM appointments a WHERE a.doctor_id = d.doctor_id
    AND a.appt_date = date('now','localtime','+1 day') AND a.slot_time = '10:00'
    AND a.status NOT IN ('CANCELLED','NO_SHOW'));

-- Waiting patients with position and estimated wait (view)
SELECT doctor_name, token_no, patient_name, people_ahead + 1 AS position, est_wait_min
FROM v_queue WHERE queue_date = date('now','localtime') AND token_status = 'WAITING'
ORDER BY doctor_name, token_no;

-- Frequent patients (GROUP BY + HAVING)
SELECT p.full_name, COUNT(*) AS visits FROM patients p
JOIN appointments a ON a.patient_id = p.patient_id
WHERE a.status = 'COMPLETED' GROUP BY p.patient_id HAVING COUNT(*) >= 2 ORDER BY visits DESC;
```
Run them with `sqlite3 instance/hospital.db` after seeding.

## 10. Setup and use

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py --reset          # creates instance/hospital.db with demo data
python app.py                   # http://127.0.0.1:5000
python -m unittest discover -s tests -v
```
Set `SECRET_KEY` in the environment before any real deployment. Delete `instance/hospital.db` (or run `seed.py --reset`) to start fresh.

**Demo script for the viva (about 5 minutes)**
1. Dashboard: today's counts and the 7-day chart.
2. Register a new patient, then book a slot with a doctor.
3. Try to book the **same slot** for another patient: the error appears. Mention the partial unique index.
4. Reschedule it, cancel it, then open **History log** to show trigger-generated entries.
5. **Live queue:** check in two patients (tokens issued), show position and estimated wait, press **Call next**, then complete with a diagnosis.
6. Open the patient's page to show consultation history.

Note: slots for *today* that are already in the past cannot be booked, so run the demo during the doctors' working hours, or book for tomorrow and use the seeded queue for today.

## 11. Testing
`tests/test_core.py` has 27 automated tests: double booking (app level, database level, concurrent threads), patient clash,
cancel-then-rebook, invalid dates and times, reschedule, rollback on failure, foreign-key enforcement, append-only history,
token numbering and wait estimates, one-patient-at-a-time, skip and cancel recalculation, validation, CSRF, XSS escaping,
authentication (admin login, patient registration, patient portal), role-based access restrictions, and tamper prevention.

## 12. Security and validation
SQL uses bound parameters only (no string-built queries with user input). Jinja escapes output (tested with a script tag).
All POST forms carry a session CSRF token. Inputs are validated for phone, email, dates, ranges and lengths. Passwords are
hashed with Werkzeug salted hashing. Role-based access control enforces isolation between staff and patients.

## 13. Limitations and future work
Estimated wait uses a fixed consultation length (could be replaced with a moving average of recent visits); SQLite allows one
writer at a time, which is fine for one hospital desk but a server database would be used at scale; no SMS/email reminders;
walk-ins without an appointment are not modelled (an extension would add an `is_walk_in` flag and a token without a slot).

**Moving to MySQL/PostgreSQL:** replace `AUTOINCREMENT` with `AUTO_INCREMENT`/`SERIAL`, `datetime('now')` with `NOW()`, and
`BEGIN IMMEDIATE` with `START TRANSACTION` plus `SELECT ... FOR UPDATE`. PostgreSQL supports the same partial unique indexes;
in MySQL use a generated column (`live_slot = IF(status IN ('CANCELLED','NO_SHOW'), NULL, slot_time)`) with a unique index.

## 14. Likely viva questions

* **How do you stop double booking?** Partial unique index on `(doctor_id, appt_date, slot_time)` for live statuses, plus a `BEGIN IMMEDIATE` transaction with a pre-check (section 6).
* **Why a partial index?** So cancelled and no-show rows stay as history but do not block re-booking.
* **Why transactions?** Multi-table changes (token + status + consultation) must be all-or-nothing (ACID: atomicity, isolation).
* **Why are `doctor_id`/`queue_date` repeated in `queue_tokens`?** To enforce unique token numbers per doctor per day; kept consistent by writing them in the same transaction.
* **How is the wait estimated?** People ahead x consultation minutes, computed in view `v_queue`.
* **Why RESTRICT on deletes?** Medical history must never be orphaned or silently deleted.
* **Which normal form?** 3NF, with the one deliberate, documented copy above.
