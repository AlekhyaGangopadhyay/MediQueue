"""Fill the database with realistic demo data.   Usage:  python seed.py [--reset]"""
import os
import random
import sys
from datetime import timedelta

import db
import services as svc
from app import create_app

DEPARTMENTS = ["General Medicine", "Cardiology", "Paediatrics", "Orthopaedics", "Dermatology"]
# name, dept, specialization, phone, email, minutes, weekdays(0=Mon), start, end
DOCTORS = [
    ("Dr. Anirban Sen",     "General Medicine", "Physician",        "9830010001", "anirban.sen@mediqueue.test",  10, range(0, 7), "09:00", "14:00"),
    ("Dr. Meera Banerjee",  "Cardiology",       "Cardiologist",     "9830010002", "meera.banerjee@mediqueue.test", 20, range(0, 6), "10:00", "15:00"),
    ("Dr. Rohan Das",       "Paediatrics",      "Child specialist", "9830010003", "rohan.das@mediqueue.test",    15, range(0, 6), "09:30", "13:30"),
    ("Dr. Sunita Roy",      "Orthopaedics",     "Orthopaedic surgeon", "9830010004", "sunita.roy@mediqueue.test", 15, range(0, 6), "11:00", "16:00"),
    ("Dr. Farhan Ahmed",    "Dermatology",      "Dermatologist",    "9830010005", "farhan.ahmed@mediqueue.test", 15, range(0, 6), "10:00", "14:00"),
]
PATIENTS = [
    ("Aditi Mukherjee", "1994-03-12", "F"), ("Rahul Ghosh", "1988-11-02", "M"), ("Priya Chatterjee", "2001-07-25", "F"),
    ("Sourav Dutta", "1975-01-30", "M"), ("Ishita Bose", "1999-09-09", "F"), ("Kunal Sarkar", "1983-05-18", "M"),
    ("Tanushree Paul", "1968-12-21", "F"), ("Arjun Mitra", "2015-04-04", "M"), ("Riya Saha", "2012-08-16", "F"),
    ("Debashis Nandi", "1959-02-11", "M"), ("Sneha Kar", "1991-10-05", "F"), ("Imran Sheikh", "1985-06-27", "M"),
    ("Moumita Pal", "1996-01-14", "F"), ("Vikram Singh", "1979-03-03", "M"), ("Nandini Basu", "2003-11-19", "F"),
]
REASONS = ["Fever and cough", "Routine check-up", "Follow-up visit", "Chest discomfort", "Skin rash",
           "Joint pain", "Vaccination", "Headache", "Test report review"]
DIAGNOSES = [("Viral fever", "Paracetamol 500 mg, fluids"), ("Hypertension, stable", "Continue amlodipine"),
             ("Seasonal allergy", "Cetirizine 10 mg at night"), ("Mild sprain", "Rest, ice, ibuprofen 3 days")]


def seed(conn):
    rnd = random.Random(42)
    with db.transaction(conn):
        conn.executemany("INSERT INTO departments (name) VALUES (?)", [(d,) for d in DEPARTMENTS])
        admin_pwd = svc.generate_password_hash("admin123")
        conn.execute("INSERT INTO admins (username, password_hash, full_name) VALUES (?,?,?)",
                     ("admin", admin_pwd, "Hospital Administrator"))
        for name, dept, spec, phone, email, mins, days, start, end in DOCTORS:
            dept_id = conn.execute("SELECT dept_id FROM departments WHERE name=?", (dept,)).fetchone()[0]
            cur = conn.execute("INSERT INTO doctors (full_name, dept_id, specialization, phone, email, consult_minutes) "
                               "VALUES (?,?,?,?,?,?)", (name, dept_id, spec, phone, email, mins))
            conn.executemany("INSERT INTO doctor_schedules (doctor_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
                             [(cur.lastrowid, d, start, end) for d in days])
        patient_pwd = svc.generate_password_hash("patient123")
        for i, (name, dob, g) in enumerate(PATIENTS):
            conn.execute("INSERT INTO patients (full_name, date_of_birth, gender, phone, email, password_hash) VALUES (?,?,?,?,?,?)",
                         (name, dob, g, f"98310000{i:02d}", f"patient{i+1}@mediqueue.test", patient_pwd))

    patient_ids = [r[0] for r in conn.execute("SELECT patient_id FROM patients")]
    doctors = conn.execute("SELECT doctor_id FROM doctors").fetchall()
    used = set()

    def slots_for(doctor_id, day):
        return [s["time"] for s in svc.generate_slots(conn, doctor_id, day.isoformat())]

    def add_direct(doctor_id, day, slot, status):
        pid = rnd.choice(patient_ids)
        if (pid, day) in used:          # one visit per patient per day keeps the demo realistic
            return None
        used.add((pid, day))
        cur = conn.execute("INSERT INTO appointments (patient_id, doctor_id, appt_date, slot_time, status, reason) "
                           "VALUES (?,?,?,?,?,?)", (pid, doctor_id, day.isoformat(), slot, status, rnd.choice(REASONS)))
        return cur.lastrowid

    # Past week: mostly completed, a few cancelled
    for back in range(1, 7):
        day = svc.today() - timedelta(days=back)
        for d in doctors:
            slots = slots_for(d["doctor_id"], day)
            for slot in rnd.sample(slots, min(len(slots), rnd.randint(2, 5))) if slots else []:
                status = "COMPLETED" if rnd.random() < 0.85 else "CANCELLED"
                aid = add_direct(d["doctor_id"], day, slot, status)
                if aid and status == "COMPLETED":
                    dx, rx = rnd.choice(DIAGNOSES)
                    conn.execute("INSERT INTO consultations (appointment_id, started_at, ended_at, diagnosis, prescription) "
                                 "VALUES (?,?,?,?,?)", (aid, f"{day} {slot}:00", f"{day} {slot}:00", dx, rx))
    # Tomorrow and the day after: booked
    for ahead in (1, 2):
        day = svc.today() + timedelta(days=ahead)
        for d in doctors:
            slots = slots_for(d["doctor_id"], day)
            for slot in rnd.sample(slots, min(len(slots), 3)) if slots else []:
                add_direct(d["doctor_id"], day, slot, "BOOKED")
    # Today: book through the real service layer-style rows, then drive the queue with real transactions
    day = svc.today()
    first = {}
    for d in doctors:
        slots = slots_for(d["doctor_id"], day)[:6]
        ids = [add_direct(d["doctor_id"], day, s, "BOOKED") for s in slots]
        first[d["doctor_id"]] = [i for i in ids if i]
    for doctor_id, ids in first.items():
        for aid in ids[:4]:
            svc.check_in(conn, aid)
    order = list(first)
    if len(order) >= 2:
        svc.call_next(conn, order[1])
        svc.complete_consultation(conn, first[order[1]][0], "Mild hypertension", "Amlodipine 5 mg daily", "Review in 2 weeks")
        svc.call_next(conn, order[1])
    svc.call_next(conn, order[0])


if __name__ == "__main__":
    app = create_app()
    path = app.config["DATABASE"]
    if "--reset" in sys.argv:
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(path + suffix):
                os.remove(path + suffix)
        app = create_app()
    conn = db.connect(path)
    if conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]:
        sys.exit("Database already has data. Run:  python seed.py --reset")
    seed(conn)
    conn.close()
    print("Seeded demo data into", path)
