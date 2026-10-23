-- =====================================================================
-- Hospital Appointment & Queue Management System  -  schema (SQLite)
-- Integrated with HMS_aiml_22 (Departments, Doctors, Patients,
-- Rooms, Staff, Billing, Lab Tests, Medical Records)
-- =====================================================================
PRAGMA foreign_keys = ON;

-- ---------- Reference data -------------------------------------------
CREATE TABLE departments (
    dept_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL UNIQUE,
    location  TEXT,
    phone     TEXT
);

-- ---------- Doctors ----------------------------------------------------
CREATE TABLE doctors (
    doctor_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT    NOT NULL,
    dept_id         INTEGER NOT NULL
                    REFERENCES departments(dept_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    specialization  TEXT    NOT NULL,
    phone           TEXT    NOT NULL UNIQUE,
    email           TEXT    NOT NULL UNIQUE,
    consult_minutes INTEGER NOT NULL DEFAULT 15 CHECK (consult_minutes BETWEEN 5 AND 120),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Weekly working hours. weekday: 0 = Monday ... 6 = Sunday. One row per doctor per weekday.
CREATE TABLE doctor_schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id   INTEGER NOT NULL REFERENCES doctors(doctor_id) ON DELETE CASCADE,
    weekday     INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    start_time  TEXT    NOT NULL CHECK (start_time GLOB '[0-2][0-9]:[0-5][0-9]'),
    end_time    TEXT    NOT NULL CHECK (end_time   GLOB '[0-2][0-9]:[0-5][0-9]'),
    CHECK (start_time < end_time),
    UNIQUE (doctor_id, weekday)
);

-- ---------- Admins / Staff ---------------------------------------------
CREATE TABLE admins (
    admin_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------- Patients ---------------------------------------------------
CREATE TABLE patients (
    patient_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    gender        TEXT NOT NULL CHECK (gender IN ('M', 'F', 'O', 'Male', 'Female', 'Other')),
    phone         TEXT NOT NULL UNIQUE,
    email         TEXT UNIQUE,
    address       TEXT,
    blood_group   TEXT,
    password_hash TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ---------- Rooms & Wards ----------------------------------------------
CREATE TABLE rooms (
    room_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    room_no       TEXT NOT NULL UNIQUE,
    room_type     TEXT NOT NULL,
    floor         INTEGER,
    status        TEXT NOT NULL DEFAULT 'Available',
    daily_charge  REAL NOT NULL DEFAULT 1000.0,
    dept_id       INTEGER REFERENCES departments(dept_id) ON DELETE SET NULL
);

-- ---------- Staff ------------------------------------------------------
CREATE TABLE staff (
    staff_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT NOT NULL,
    role        TEXT NOT NULL,
    phone       TEXT,
    email       TEXT,
    room_id     INTEGER REFERENCES rooms(room_id) ON DELETE SET NULL
);

-- ---------- Appointments ------------------------------------------------
CREATE TABLE appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id     INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
    doctor_id      INTEGER NOT NULL REFERENCES doctors(doctor_id)   ON DELETE RESTRICT,
    appt_date      TEXT    NOT NULL,                       -- YYYY-MM-DD
    slot_time      TEXT    NOT NULL CHECK (slot_time GLOB '[0-2][0-9]:[0-5][0-9]'),
    status         TEXT    NOT NULL DEFAULT 'BOOKED'
                   CHECK (status IN ('BOOKED','CHECKED_IN','IN_CONSULTATION',
                                     'COMPLETED','CANCELLED','NO_SHOW')),
    reason         TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- DOUBLE-BOOKING PREVENTION:
CREATE UNIQUE INDEX uq_doctor_slot_live
    ON appointments (doctor_id, appt_date, slot_time)
    WHERE status NOT IN ('CANCELLED', 'NO_SHOW');

CREATE UNIQUE INDEX uq_patient_slot_live
    ON appointments (patient_id, appt_date, slot_time)
    WHERE status NOT IN ('CANCELLED', 'NO_SHOW');

CREATE INDEX idx_appt_date   ON appointments (appt_date);
CREATE INDEX idx_appt_doctor ON appointments (doctor_id, appt_date);

-- ---------- Queue tokens ------------------------------------------------
CREATE TABLE queue_tokens (
    token_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointments(appointment_id) ON DELETE RESTRICT,
    doctor_id      INTEGER NOT NULL REFERENCES doctors(doctor_id) ON DELETE RESTRICT,
    queue_date     TEXT    NOT NULL,
    token_no       INTEGER NOT NULL CHECK (token_no > 0),
    status         TEXT    NOT NULL DEFAULT 'WAITING'
                   CHECK (status IN ('WAITING','CALLED','DONE','SKIPPED','CANCELLED')),
    issued_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    called_at      TEXT,
    completed_at   TEXT,
    UNIQUE (doctor_id, queue_date, token_no)
);

CREATE UNIQUE INDEX uq_one_called_per_doctor
    ON queue_tokens (doctor_id, queue_date)
    WHERE status = 'CALLED';

-- ---------- Consultation history & Medical Records ----------------------
CREATE TABLE consultations (
    consultation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id  INTEGER NOT NULL UNIQUE REFERENCES appointments(appointment_id) ON DELETE RESTRICT,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    diagnosis       TEXT,
    prescription    TEXT,
    treatment       TEXT,
    notes           TEXT
);

-- ---------- Laboratory & Tests ------------------------------------------
CREATE TABLE tests (
    test_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name TEXT NOT NULL,
    test_type TEXT,
    cost      REAL NOT NULL
);

CREATE TABLE test_results (
    result_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id      INTEGER NOT NULL REFERENCES tests(test_id) ON DELETE RESTRICT,
    patient_id   INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
    result_value TEXT,
    unit         TEXT,
    normal_range TEXT,
    result_date  TEXT NOT NULL
);

CREATE TABLE test_bookings (
    booking_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id       INTEGER NOT NULL REFERENCES tests(test_id) ON DELETE RESTRICT,
    patient_id    INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
    booking_date  TEXT NOT NULL,
    slot_time     TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'BOOKED' CHECK (status IN ('BOOKED','COMPLETED','CANCELLED')),
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX idx_test_bookings_patient ON test_bookings(patient_id, booking_date);
CREATE INDEX idx_test_bookings_status ON test_bookings(status);

-- ---------- Billing & Payments ------------------------------------------
CREATE TABLE bills (
    bill_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id     INTEGER NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
    bill_date      TEXT NOT NULL,
    total_amount   REAL NOT NULL,
    amount_paid    REAL NOT NULL DEFAULT 0.0,
    payment_status TEXT NOT NULL DEFAULT 'Pending'
);

CREATE TABLE payments (
    payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id        INTEGER NOT NULL REFERENCES bills(bill_id) ON DELETE CASCADE,
    payment_date   TEXT NOT NULL,
    amount         REAL NOT NULL,
    payment_mode   TEXT NOT NULL,
    transaction_no TEXT NOT NULL
);

-- ---------- Appointment history (append-only audit trail) ---------------
CREATE TABLE appointment_history (
    history_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL REFERENCES appointments(appointment_id) ON DELETE RESTRICT,
    action         TEXT NOT NULL,
    old_status     TEXT,
    new_status     TEXT,
    old_date       TEXT,
    old_time       TEXT,
    new_date       TEXT,
    new_time       TEXT,
    changed_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TRIGGER trg_appt_created AFTER INSERT ON appointments
BEGIN
    INSERT INTO appointment_history (appointment_id, action, new_status, new_date, new_time)
    VALUES (NEW.appointment_id, 'BOOKED', NEW.status, NEW.appt_date, NEW.slot_time);
END;

CREATE TRIGGER trg_appt_changed AFTER UPDATE ON appointments
WHEN OLD.status <> NEW.status OR OLD.appt_date <> NEW.appt_date OR OLD.slot_time <> NEW.slot_time
BEGIN
    INSERT INTO appointment_history
        (appointment_id, action, old_status, new_status, old_date, old_time, new_date, new_time)
    VALUES (
        NEW.appointment_id,
        CASE WHEN OLD.appt_date <> NEW.appt_date OR OLD.slot_time <> NEW.slot_time
             THEN 'RESCHEDULED' ELSE NEW.status END,
        OLD.status, NEW.status, OLD.appt_date, OLD.slot_time, NEW.appt_date, NEW.slot_time);
END;

CREATE TRIGGER trg_history_no_update BEFORE UPDATE ON appointment_history
BEGIN SELECT RAISE(ABORT, 'appointment_history is append-only'); END;

CREATE TRIGGER trg_history_no_delete BEFORE DELETE ON appointment_history
BEGIN SELECT RAISE(ABORT, 'appointment_history is append-only'); END;

-- ---------- Views ---------------------------------------------------------
CREATE VIEW v_queue AS
SELECT  t.token_id, t.token_no, t.status AS token_status, t.queue_date, t.issued_at, t.called_at,
        a.appointment_id, a.slot_time, a.reason,
        p.patient_id, p.full_name AS patient_name,
        d.doctor_id,  d.full_name AS doctor_name, d.consult_minutes,
        (SELECT COUNT(*) FROM queue_tokens q
          WHERE q.doctor_id  = t.doctor_id
            AND q.queue_date = t.queue_date
            AND q.status IN ('WAITING', 'CALLED')
            AND q.token_no   < t.token_no)                       AS people_ahead,
        (SELECT COUNT(*) FROM queue_tokens q
          WHERE q.doctor_id  = t.doctor_id
            AND q.queue_date = t.queue_date
            AND q.status IN ('WAITING', 'CALLED')
            AND q.token_no   < t.token_no) * d.consult_minutes   AS est_wait_min
FROM queue_tokens t
JOIN appointments a ON a.appointment_id = t.appointment_id
JOIN patients     p ON p.patient_id     = a.patient_id
JOIN doctors      d ON d.doctor_id      = t.doctor_id;
