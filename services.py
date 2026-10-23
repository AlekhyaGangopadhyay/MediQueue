"""Business logic. Every state change that touches more than one row runs inside a
transaction so the database never ends up half-updated."""
import re
import sqlite3
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

from db import transaction

MAX_ADVANCE_DAYS = 30
LIVE_SQL = "('CANCELLED','NO_SHOW')"          # statuses that free a slot
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_PHONE_RE = re.compile(r"^\+?\d{10,15}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class AppError(Exception):
    """A problem the user can fix; the message is shown to them."""


# ------------------------------------------------------------------ helpers
def today():
    return date.today()


def _clean(value):
    return (value or "").strip()


def _phone(value):
    p = re.sub(r"[\s\-()]", "", _clean(value))
    if not _PHONE_RE.match(p):
        raise AppError("Enter a valid phone number (10-15 digits, optional leading +).")
    return p


def _email(value, required=False):
    e = _clean(value).lower()
    if not e:
        if required:
            raise AppError("Email is required.")
        return None
    if not _EMAIL_RE.match(e):
        raise AppError("Enter a valid email address.")
    return e


def parse_date(value):
    try:
        return datetime.strptime(_clean(value), "%Y-%m-%d").date()
    except ValueError:
        raise AppError("Enter a valid date (YYYY-MM-DD).")


def _hm_to_min(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def _min_to_hm(n):
    return f"{n // 60:02d}:{n % 60:02d}"


def _integrity_message(exc):
    msg = str(exc)
    if "appointments.doctor_id" in msg:
        return "That slot has just been booked by someone else. Please pick another slot."
    if "appointments.patient_id" in msg:
        return "This patient already has an appointment at that date and time."
    if "patients.phone" in msg or "doctors.phone" in msg:
        return "That phone number is already registered."
    if "email" in msg:
        return "That email address is already registered."
    return f"The database rejected this change ({msg})."


# ------------------------------------------------------------------ auth & admins
def add_admin(conn, username, password, full_name="Admin"):
    user = _clean(username).lower()
    if len(user) < 3:
        raise AppError("Username must have at least 3 characters.")
    pwd = _clean(password)
    if len(pwd) < 4:
        raise AppError("Password must have at least 4 characters.")
    pwd_hash = generate_password_hash(pwd)
    try:
        with transaction(conn):
            cur = conn.execute(
                "INSERT INTO admins (username, password_hash, full_name) VALUES (?,?,?)",
                (user, pwd_hash, _clean(full_name) or "Administrator"))
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise AppError("That admin username is already registered.")


def authenticate_admin(conn, username, password):
    user = _clean(username).lower()
    if not user or not password:
        return None
    row = conn.execute("SELECT * FROM admins WHERE LOWER(username) = ?", (user,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return row
    return None


# ------------------------------------------------------------------ patients
def add_patient(conn, form, password=None):
    name = _clean(form.get("full_name"))
    if len(name) < 2:
        raise AppError("Patient name must have at least 2 characters.")
    dob = parse_date(form.get("date_of_birth"))
    if dob > today():
        raise AppError("Date of birth cannot be in the future.")
    gender = _clean(form.get("gender"))
    if gender not in ("M", "F", "O", "Male", "Female", "Other"):
        raise AppError("Select a gender.")
    phone, email = _phone(form.get("phone")), _email(form.get("email"))
    blood_group = _clean(form.get("blood_group")) or None
    pwd = password or form.get("password") or "patient123"
    if len(pwd) < 4:
        raise AppError("Password must have at least 4 characters.")
    pwd_hash = generate_password_hash(pwd)
    try:
        with transaction(conn):
            cur = conn.execute(
                "INSERT INTO patients (full_name, date_of_birth, gender, phone, email, address, blood_group, password_hash) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (name, dob.isoformat(), gender, phone, email, _clean(form.get("address")) or None, blood_group, pwd_hash))
    except sqlite3.IntegrityError as exc:
        raise AppError(_integrity_message(exc))
    return cur.lastrowid


def authenticate_patient(conn, identifier, password):
    ident = _clean(identifier)
    if not ident or not password:
        return None
    clean_phone = re.sub(r"[\s\-()]", "", ident)
    row = conn.execute(
        "SELECT * FROM patients WHERE phone = ? OR LOWER(email) = ?",
        (clean_phone, ident.lower())
    ).fetchone()
    if row and row["password_hash"] and check_password_hash(row["password_hash"], password):
        return row
    return None


def patient_portal_data(conn, patient_id):
    patient = get_patient(conn, patient_id)
    day = today().isoformat()
    # Today's active appointments with queue position and estimated wait
    today_appts = conn.execute(
        """SELECT a.*, d.full_name AS doctor_name, dep.name AS department, d.consult_minutes,
                  vq.token_no, vq.token_status, vq.people_ahead, vq.est_wait_min
           FROM appointments a
           JOIN doctors d ON d.doctor_id = a.doctor_id
           JOIN departments dep ON dep.dept_id = d.dept_id
           LEFT JOIN v_queue vq ON vq.appointment_id = a.appointment_id
           WHERE a.patient_id = ? AND a.appt_date = ?
           ORDER BY a.slot_time ASC""", (patient_id, day)).fetchall()
    # Upcoming appointments
    upcoming_appts = conn.execute(
        """SELECT a.*, d.full_name AS doctor_name, dep.name AS department
           FROM appointments a
           JOIN doctors d ON d.doctor_id = a.doctor_id
           JOIN departments dep ON dep.dept_id = d.dept_id
           WHERE a.patient_id = ? AND a.appt_date > ? AND a.status NOT IN ('CANCELLED', 'NO_SHOW')
           ORDER BY a.appt_date ASC, a.slot_time ASC""", (patient_id, day)).fetchall()
    # Past consultation & medical record history
    history = patient_history(conn, patient_id)
    bills = list_bills(conn, patient_id)
    tests = list_test_results(conn, patient_id)
    return {
        "patient": patient,
        "today_appts": today_appts,
        "upcoming_appts": upcoming_appts,
        "history": history,
        "bills": bills,
        "tests": tests
    }


def list_patients(conn, q=""):
    q = _clean(q)
    sql = ("SELECT p.*, (SELECT COUNT(*) FROM appointments a WHERE a.patient_id = p.patient_id) AS visits "
           "FROM patients p ")
    args = ()
    if q:
        sql += "WHERE p.full_name LIKE ? OR p.phone LIKE ? OR p.blood_group LIKE ? "
        args = (f"%{q}%", f"%{q}%", f"%{q}%")
    return conn.execute(sql + "ORDER BY p.full_name", args).fetchall()


def get_patient(conn, patient_id):
    row = conn.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    if not row:
        raise AppError("Patient not found.")
    return row


def patient_history(conn, patient_id):
    """Appointments + consultation notes for one patient (JOIN across 4 tables)."""
    return conn.execute(
        """SELECT a.appointment_id, a.appt_date, a.slot_time, a.status, a.reason,
                  d.full_name AS doctor_name, dep.name AS department,
                  c.diagnosis, c.prescription, c.treatment, c.notes
           FROM appointments a
           JOIN doctors d      ON d.doctor_id = a.doctor_id
           JOIN departments dep ON dep.dept_id = d.dept_id
           LEFT JOIN consultations c ON c.appointment_id = a.appointment_id
           WHERE a.patient_id = ?
           ORDER BY a.appt_date DESC, a.slot_time DESC""", (patient_id,)).fetchall()


# ------------------------------------------------------------------ Rooms, Staff, Billing, Tests (HMS_aiml_22)
def list_rooms(conn):
    return conn.execute(
        """SELECT r.*, dep.name AS department_name
           FROM rooms r
           LEFT JOIN departments dep ON dep.dept_id = r.dept_id
           ORDER BY r.floor ASC, r.room_no ASC"""
    ).fetchall()


def list_staff(conn):
    return conn.execute(
        """SELECT s.*, r.room_no, r.room_type, r.floor
           FROM staff s
           LEFT JOIN rooms r ON r.room_id = s.room_id
           ORDER BY s.role ASC, s.full_name ASC"""
    ).fetchall()


def list_bills(conn, patient_id=None):
    sql = """SELECT b.*, p.full_name AS patient_name, p.phone AS patient_phone,
                    (SELECT group_concat(pm.payment_mode || ': ₹' || CAST(pm.amount AS INT) || ' (' || pm.transaction_no || ')', ' · ')
                     FROM payments pm WHERE pm.bill_id = b.bill_id) AS payment_details
             FROM bills b
             JOIN patients p ON p.patient_id = b.patient_id """
    args = []
    if patient_id:
        sql += "WHERE b.patient_id = ? "
        args.append(patient_id)
    return conn.execute(sql + "ORDER BY b.bill_date DESC, b.bill_id DESC", args).fetchall()


def list_tests(conn):
    return conn.execute("SELECT * FROM tests ORDER BY test_type, test_name").fetchall()


def list_test_results(conn, patient_id=None):
    sql = """SELECT tr.*, t.test_name, t.test_type, t.cost, p.full_name AS patient_name, p.phone AS patient_phone
             FROM test_results tr
             JOIN tests t ON t.test_id = tr.test_id
             JOIN patients p ON p.patient_id = tr.patient_id """
    args = []
    if patient_id:
        sql += "WHERE tr.patient_id = ? "
        args.append(patient_id)
    return conn.execute(sql + "ORDER BY tr.result_date DESC, tr.result_id DESC", args).fetchall()


# ------------------------------------------------------------------ doctors
def list_departments(conn):
    return conn.execute("SELECT * FROM departments ORDER BY name").fetchall()


def add_doctor(conn, form, weekdays):
    name = _clean(form.get("full_name"))
    if len(name) < 2:
        raise AppError("Doctor name must have at least 2 characters.")
    spec = _clean(form.get("specialization"))
    if not spec:
        raise AppError("Specialization is required.")
    phone, email = _phone(form.get("phone")), _email(form.get("email"), required=True)
    try:
        minutes = int(form.get("consult_minutes") or 15)
    except ValueError:
        raise AppError("Consultation length must be a number of minutes.")
    if not 5 <= minutes <= 120:
        raise AppError("Consultation length must be between 5 and 120 minutes.")
    start, end = _clean(form.get("start_time")), _clean(form.get("end_time"))
    if not (_TIME_RE.match(start) and _TIME_RE.match(end)):
        raise AppError("Enter working hours as HH:MM.")
    if _hm_to_min(end) - _hm_to_min(start) < minutes:
        raise AppError("Working hours must be at least one consultation long.")
    days = sorted({int(d) for d in weekdays if str(d).isdigit() and 0 <= int(d) <= 6})
    if not days:
        raise AppError("Select at least one working day.")
    new_dept = _clean(form.get("new_department"))
    try:
        with transaction(conn):
            if new_dept:
                conn.execute("INSERT OR IGNORE INTO departments (name) VALUES (?)", (new_dept,))
                dept = conn.execute("SELECT dept_id FROM departments WHERE name = ?", (new_dept,)).fetchone()
            else:
                dept = conn.execute("SELECT dept_id FROM departments WHERE dept_id = ?",
                                    (form.get("dept_id"),)).fetchone()
            if not dept:
                raise AppError("Select a department.")
            cur = conn.execute(
                "INSERT INTO doctors (full_name, dept_id, specialization, phone, email, consult_minutes) "
                "VALUES (?,?,?,?,?,?)", (name, dept["dept_id"], spec, phone, email, minutes))
            conn.executemany(
                "INSERT INTO doctor_schedules (doctor_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
                [(cur.lastrowid, d, start, end) for d in days])
    except sqlite3.IntegrityError as exc:
        raise AppError(_integrity_message(exc))
    return cur.lastrowid


def list_doctors(conn, active_only=False):
    sql = ("SELECT d.*, dep.name AS department, "
           "(SELECT group_concat(substr('MonTueWedThuFriSatSun', weekday*3+1, 3), ' ') "
           "   FROM (SELECT weekday FROM doctor_schedules s WHERE s.doctor_id = d.doctor_id ORDER BY weekday)) AS days, "
           "(SELECT start_time || '-' || end_time FROM doctor_schedules s WHERE s.doctor_id = d.doctor_id LIMIT 1) AS hours "
           "FROM doctors d JOIN departments dep ON dep.dept_id = d.dept_id ")
    if active_only:
        sql += "WHERE d.is_active = 1 "
    return conn.execute(sql + "ORDER BY d.full_name").fetchall()


def get_doctor(conn, doctor_id):
    row = conn.execute("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,)).fetchone()
    if not row:
        raise AppError("Doctor not found.")
    return row


# ------------------------------------------------------------------ slots
def generate_slots(conn, doctor_id, date_str, exclude_appt_id=None):
    """All slots for a doctor on a date, each flagged available / not."""
    d = parse_date(date_str)
    doc = conn.execute("SELECT consult_minutes, is_active FROM doctors WHERE doctor_id = ?",
                       (doctor_id,)).fetchone()
    if not doc or not doc["is_active"]:
        return []
    sch = conn.execute("SELECT start_time, end_time FROM doctor_schedules WHERE doctor_id = ? AND weekday = ?",
                       (doctor_id, d.weekday())).fetchone()
    if not sch:
        return []
    taken = {r["slot_time"] for r in conn.execute(
        f"SELECT slot_time FROM appointments WHERE doctor_id = ? AND appt_date = ? "
        f"AND status NOT IN {LIVE_SQL} AND appointment_id <> ?",
        (doctor_id, d.isoformat(), exclude_appt_id or -1))}
    now_hm = datetime.now().strftime("%H:%M") if d == today() else None
    step, t, end = doc["consult_minutes"], _hm_to_min(sch["start_time"]), _hm_to_min(sch["end_time"])
    slots = []
    while t + step <= end:
        hm = _min_to_hm(t)
        slots.append({"time": hm, "available": hm not in taken and (now_hm is None or hm > now_hm)})
        t += step
    return slots


def _validate_slot(conn, patient_id, doctor_id, date_str, slot_time, exclude_appt_id=None):
    d = parse_date(date_str)
    if d < today():
        raise AppError("You cannot book a date in the past.")
    if d > today() + timedelta(days=MAX_ADVANCE_DAYS):
        raise AppError(f"Appointments can be booked at most {MAX_ADVANCE_DAYS} days ahead.")
    doc = get_doctor(conn, doctor_id)
    if not doc["is_active"]:
        raise AppError("This doctor is not accepting appointments.")
    slot = next((s for s in generate_slots(conn, doctor_id, date_str, exclude_appt_id)
                 if s["time"] == slot_time), None)
    if slot is None:
        raise AppError("That time is outside the doctor's working hours or consultation slots.")
    if not slot["available"]:
        raise AppError("That slot is already booked or has passed. Please pick another slot.")
    clash = conn.execute(
        f"SELECT 1 FROM appointments WHERE patient_id = ? AND appt_date = ? AND slot_time = ? "
        f"AND status NOT IN {LIVE_SQL} AND appointment_id <> ?",
        (patient_id, d.isoformat(), slot_time, exclude_appt_id or -1)).fetchone()
    if clash:
        raise AppError("This patient already has an appointment at that date and time.")
    return d


# ------------------------------------------------------------------ appointments
def book_appointment(conn, patient_id, doctor_id, date_str, slot_time, reason=""):
    try:
        with transaction(conn):
            get_patient(conn, patient_id)
            d = _validate_slot(conn, patient_id, doctor_id, date_str, slot_time)
            cur = conn.execute(
                "INSERT INTO appointments (patient_id, doctor_id, appt_date, slot_time, reason) "
                "VALUES (?,?,?,?,?)",
                (patient_id, doctor_id, d.isoformat(), slot_time, _clean(reason) or None))
    except sqlite3.IntegrityError as exc:   # last line of defence: the unique indexes
        raise AppError(_integrity_message(exc))
    return cur.lastrowid


def _get_appt(conn, appt_id):
    row = conn.execute("SELECT * FROM appointments WHERE appointment_id = ?", (appt_id,)).fetchone()
    if not row:
        raise AppError("Appointment not found.")
    return row


def get_appointment_detail(conn, appt_id):
    row = conn.execute(
        """SELECT a.*, p.full_name AS patient_name, d.full_name AS doctor_name
           FROM appointments a JOIN patients p ON p.patient_id = a.patient_id
           JOIN doctors d ON d.doctor_id = a.doctor_id WHERE a.appointment_id = ?""",
        (appt_id,)).fetchone()
    if not row:
        raise AppError("Appointment not found.")
    return row


def reschedule_appointment(conn, appt_id, date_str, slot_time):
    try:
        with transaction(conn):
            a = _get_appt(conn, appt_id)
            if a["status"] != "BOOKED":
                raise AppError("Only appointments that are still 'Booked' can be rescheduled.")
            if a["appt_date"] == _clean(date_str) and a["slot_time"] == slot_time:
                raise AppError("Choose a different date or time.")
            d = _validate_slot(conn, a["patient_id"], a["doctor_id"], date_str, slot_time,
                               exclude_appt_id=appt_id)
            conn.execute("UPDATE appointments SET appt_date = ?, slot_time = ? WHERE appointment_id = ?",
                         (d.isoformat(), slot_time, appt_id))
    except sqlite3.IntegrityError as exc:
        raise AppError(_integrity_message(exc))


def cancel_appointment(conn, appt_id):
    with transaction(conn):
        a = _get_appt(conn, appt_id)
        if a["status"] not in ("BOOKED", "CHECKED_IN"):
            raise AppError("Only 'Booked' or 'Checked in' appointments can be cancelled.")
        conn.execute("UPDATE appointments SET status = 'CANCELLED' WHERE appointment_id = ?", (appt_id,))
        conn.execute("UPDATE queue_tokens SET status = 'CANCELLED' "
                     "WHERE appointment_id = ? AND status = 'WAITING'", (appt_id,))


def list_appointments(conn, date_str="", doctor_id="", status="", q=""):
    sql = """SELECT a.*, p.full_name AS patient_name, p.phone AS patient_phone,
                    d.full_name AS doctor_name, vq.token_no, vq.token_status,
                    vq.people_ahead, vq.est_wait_min
             FROM appointments a
             JOIN patients p ON p.patient_id = a.patient_id
             JOIN doctors  d ON d.doctor_id  = a.doctor_id
             LEFT JOIN v_queue vq ON vq.appointment_id = a.appointment_id
             WHERE 1=1 """
    args = []
    if _clean(date_str):
        sql += "AND a.appt_date = ? "
        args.append(parse_date(date_str).isoformat())
    if _clean(doctor_id).isdigit():
        sql += "AND a.doctor_id = ? "
        args.append(int(doctor_id))
    if _clean(status):
        sql += "AND a.status = ? "
        args.append(_clean(status))
    if _clean(q):
        sql += "AND (p.full_name LIKE ? OR p.phone LIKE ?) "
        args += [f"%{_clean(q)}%"] * 2
    return conn.execute(sql + "ORDER BY a.appt_date DESC, a.slot_time ASC LIMIT 300", args).fetchall()


# ------------------------------------------------------------------ queue
def check_in(conn, appt_id):
    """Issue the next token number for this doctor today (transaction => no duplicate numbers)."""
    with transaction(conn):
        a = _get_appt(conn, appt_id)
        if a["status"] != "BOOKED":
            raise AppError("Only 'Booked' appointments can be checked in.")
        if a["appt_date"] != today().isoformat():
            raise AppError("Check-in is only possible on the day of the appointment.")
        n = conn.execute("SELECT COALESCE(MAX(token_no), 0) + 1 FROM queue_tokens "
                         "WHERE doctor_id = ? AND queue_date = ?", (a["doctor_id"], a["appt_date"])).fetchone()[0]
        conn.execute("INSERT INTO queue_tokens (appointment_id, doctor_id, queue_date, token_no) "
                     "VALUES (?,?,?,?)", (appt_id, a["doctor_id"], a["appt_date"], n))
        conn.execute("UPDATE appointments SET status = 'CHECKED_IN' WHERE appointment_id = ?", (appt_id,))
    return n


def call_next(conn, doctor_id):
    day = today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with transaction(conn):
            if conn.execute("SELECT 1 FROM queue_tokens WHERE doctor_id=? AND queue_date=? AND status='CALLED'",
                            (doctor_id, day)).fetchone():
                raise AppError("Finish the current consultation before calling the next patient.")
            tok = conn.execute("SELECT token_id, appointment_id, token_no FROM queue_tokens "
                               "WHERE doctor_id=? AND queue_date=? AND status='WAITING' "
                               "ORDER BY token_no LIMIT 1", (doctor_id, day)).fetchone()
            if not tok:
                raise AppError("No patients are waiting for this doctor.")
            conn.execute("UPDATE queue_tokens SET status='CALLED', called_at=? WHERE token_id=?",
                         (now, tok["token_id"]))
            conn.execute("UPDATE appointments SET status='IN_CONSULTATION' WHERE appointment_id=?",
                         (tok["appointment_id"],))
            conn.execute("INSERT INTO consultations (appointment_id, started_at) VALUES (?,?)",
                         (tok["appointment_id"], now))
    except sqlite3.IntegrityError as exc:
        raise AppError(_integrity_message(exc))
    return tok["token_no"]


def complete_consultation(conn, appt_id, diagnosis="", prescription="", notes=""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with transaction(conn):
        a = _get_appt(conn, appt_id)
        if a["status"] != "IN_CONSULTATION":
            raise AppError("This patient is not currently in consultation.")
        conn.execute("UPDATE queue_tokens SET status='DONE', completed_at=? "
                     "WHERE appointment_id=? AND status='CALLED'", (now, appt_id))
        conn.execute("UPDATE appointments SET status='COMPLETED' WHERE appointment_id=?", (appt_id,))
        conn.execute("UPDATE consultations SET ended_at=?, diagnosis=?, prescription=?, notes=? "
                     "WHERE appointment_id=?",
                     (now, _clean(diagnosis) or None, _clean(prescription) or None,
                      _clean(notes) or None, appt_id))


def skip_patient(conn, appt_id):
    """Patient was called but is absent: token is skipped, appointment becomes NO_SHOW (slot freed)."""
    with transaction(conn):
        a = _get_appt(conn, appt_id)
        if a["status"] != "CHECKED_IN":
            raise AppError("Only waiting patients can be skipped.")
        conn.execute("UPDATE queue_tokens SET status='SKIPPED' WHERE appointment_id=? AND status='WAITING'",
                     (appt_id,))
        conn.execute("UPDATE appointments SET status='NO_SHOW' WHERE appointment_id=?", (appt_id,))


def queue_board(conn):
    """One entry per doctor who has appointments today: now serving, waiting list, counters."""
    day = today().isoformat()
    doctors = conn.execute(
        """SELECT d.doctor_id, d.full_name, d.consult_minutes, dep.name AS department,
                  SUM(a.status = 'BOOKED')          AS not_arrived,
                  SUM(a.status = 'CHECKED_IN')      AS waiting,
                  SUM(a.status = 'COMPLETED')       AS done,
                  COUNT(*)                          AS total
           FROM doctors d
           JOIN departments dep ON dep.dept_id = d.dept_id
           JOIN appointments a  ON a.doctor_id = d.doctor_id AND a.appt_date = ?
                                AND a.status NOT IN ('CANCELLED','NO_SHOW')
           GROUP BY d.doctor_id ORDER BY d.full_name""", (day,)).fetchall()
    board = []
    for d in doctors:
        rows = conn.execute("SELECT * FROM v_queue WHERE doctor_id=? AND queue_date=? ORDER BY token_no",
                            (d["doctor_id"], day)).fetchall()
        arrivals = conn.execute(
            "SELECT a.appointment_id, a.slot_time, p.full_name AS patient_name FROM appointments a "
            "JOIN patients p ON p.patient_id=a.patient_id WHERE a.doctor_id=? AND a.appt_date=? "
            "AND a.status='BOOKED' ORDER BY a.slot_time", (d["doctor_id"], day)).fetchall()
        board.append({
            "doctor": d,
            "serving": next((r for r in rows if r["token_status"] == "CALLED"), None),
            "waiting": [r for r in rows if r["token_status"] == "WAITING"],
            "expected": arrivals,
        })
    return board


# ------------------------------------------------------------------ dashboard / history
def dashboard_stats(conn):
    day = today().isoformat()
    one = lambda sql, *a: conn.execute(sql, a).fetchone()[0]
    stats = {
        "doctors": one("SELECT COUNT(*) FROM doctors WHERE is_active = 1"),
        "patients": one("SELECT COUNT(*) FROM patients"),
        "today_total": one(f"SELECT COUNT(*) FROM appointments WHERE appt_date=? AND status NOT IN {LIVE_SQL}", day),
        "waiting": one("SELECT COUNT(*) FROM queue_tokens WHERE queue_date=? AND status='WAITING'", day),
        "in_consult": one("SELECT COUNT(*) FROM queue_tokens WHERE queue_date=? AND status='CALLED'", day),
        "completed": one("SELECT COUNT(*) FROM appointments WHERE appt_date=? AND status='COMPLETED'", day),
        "cancelled": one("SELECT COUNT(*) FROM appointments WHERE appt_date=? AND status='CANCELLED'", day),
    }
    start = today() - timedelta(days=6)
    counts = {r["appt_date"]: (r["total"], r["done"]) for r in conn.execute(
        f"""SELECT appt_date, COUNT(*) AS total, SUM(status='COMPLETED') AS done FROM appointments
            WHERE appt_date BETWEEN ? AND ? AND status NOT IN {LIVE_SQL} GROUP BY appt_date""",
        (start.isoformat(), day))}
    week = []
    for i in range(7):
        d = start + timedelta(days=i)
        total, done = counts.get(d.isoformat(), (0, 0))
        week.append({"label": WEEKDAYS[d.weekday()], "date": d.isoformat(), "total": total, "done": done or 0})
    peak = max([w["total"] for w in week] + [1])
    for w in week:
        w["pct"] = round(100 * w["total"] / peak)
    stats["week"] = week
    stats["status_mix"] = conn.execute(
        "SELECT status, COUNT(*) AS n FROM appointments WHERE appt_date=? GROUP BY status ORDER BY n DESC",
        (day,)).fetchall()
    stats["today_list"] = conn.execute(
        f"""SELECT a.appointment_id, a.slot_time, a.status, p.full_name AS patient_name, d.full_name AS doctor_name
            FROM appointments a JOIN patients p ON p.patient_id=a.patient_id
            JOIN doctors d ON d.doctor_id=a.doctor_id
            WHERE a.appt_date=? AND a.status NOT IN {LIVE_SQL} ORDER BY a.slot_time LIMIT 8""", (day,)).fetchall()
    return stats


def history_log(conn, appt_id=None, limit=200):
    sql = """SELECT h.*, p.full_name AS patient_name, d.full_name AS doctor_name
             FROM appointment_history h
             JOIN appointments a ON a.appointment_id = h.appointment_id
             JOIN patients p ON p.patient_id = a.patient_id
             JOIN doctors  d ON d.doctor_id  = a.doctor_id """
    args = []
    if appt_id:
        sql += "WHERE h.appointment_id = ? "
        args.append(appt_id)
    return conn.execute(sql + "ORDER BY h.history_id DESC LIMIT ?", args + [limit]).fetchall()
