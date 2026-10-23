"""Fill the database with realistic demo data from HMS_aiml_22.
Usage:  python seed.py [--reset]
"""
import os
import random
import sys
from datetime import timedelta

import db
import services as svc
from app import create_app

# 10 Departments from HMS_aiml_22 (with location and phone)
DEPARTMENTS = [
    ("Cardiology", "1st Floor", "03340000001"),
    ("Neurology", "2nd Floor", "03340000002"),
    ("Orthopedics", "3rd Floor", "03340000003"),
    ("Dermatology", "4th Floor", "03340000004"),
    ("Pediatrics", "5th Floor", "03340000005"),
    ("Gynecology", "6th Floor", "03340000006"),
    ("General Medicine", "1st Floor", "03340000007"),
    ("ENT", "2nd Floor", "03340000008"),
    ("Ophthalmology", "3rd Floor", "03340000009"),
    ("Radiology", "4th Floor", "03340000010"),
]

# 10 Doctors from HMS_aiml_22
DOCTORS = [
    ("Dr. Rajesh Kumar", "Cardiology", "Cardiologist", "9000000001", "rajesh@hospital.com", 15, range(0, 6), "09:00", "15:00"),
    ("Dr. Anita Sharma", "Dermatology", "Dermatologist", "9000000002", "anita@hospital.com", 15, range(0, 6), "10:00", "16:00"),
    ("Dr. Amit Roy", "Neurology", "Neurologist", "9000000003", "amit@hospital.com", 20, range(0, 6), "09:30", "14:30"),
    ("Dr. Priya Das", "Pediatrics", "Pediatrician", "9000000004", "priya@hospital.com", 15, range(0, 6), "10:00", "15:00"),
    ("Dr. Sourav Sen", "Orthopedics", "Orthopedic", "9000000005", "sourav@hospital.com", 15, range(0, 6), "11:00", "17:00"),
    ("Dr. Neha Ghosh", "Gynecology", "Gynecologist", "9000000006", "neha@hospital.com", 20, range(0, 6), "10:00", "15:00"),
    ("Dr. Arjun Dutta", "General Medicine", "General Physician", "9000000007", "arjun@hospital.com", 10, range(0, 7), "09:00", "14:00"),
    ("Dr. Sneha Roy", "ENT", "ENT Specialist", "9000000008", "sneha@hospital.com", 15, range(0, 6), "10:30", "15:30"),
    ("Dr. Vikash Das", "General Medicine", "Surgeon", "9000000009", "vikash@hospital.com", 15, range(0, 6), "11:00", "16:00"),
    ("Dr. Riya Sen", "General Medicine", "Psychiatrist", "9000000010", "riya@hospital.com", 20, range(0, 6), "12:00", "17:00"),
]

# 10 Patients from HMS_aiml_22 (with Blood Group, Address, Phone, Email)
PATIENTS = [
    ("Rahul Sharma", "1995-05-12", "Male", "9876543210", "rahul@gmail.com", "Kolkata", "B+"),
    ("Priya Das", "1998-08-20", "Female", "9876543211", "priya@gmail.com", "Howrah", "A+"),
    ("Amit Roy", "1990-03-15", "Male", "9876543212", "amit@gmail.com", "Durgapur", "O+"),
    ("Sneha Ghosh", "2000-11-10", "Female", "9876543213", "sneha@gmail.com", "Siliguri", "AB+"),
    ("Arjun Sen", "1988-07-25", "Male", "9876543214", "arjun@gmail.com", "Kolkata", "A-"),
    ("Riya Banerjee", "1997-01-18", "Female", "9876543215", "riya@gmail.com", "Bardhaman", "O+"),
    ("Sourav Dutta", "1993-09-05", "Male", "9876543216", "sourav@gmail.com", "Kolkata", "B+"),
    ("Ananya Mukherjee", "2001-04-22", "Female", "9876543217", "ananya@gmail.com", "Howrah", "AB-"),
    ("Vikash Chatterjee", "1985-12-30", "Male", "9876543218", "vikash@gmail.com", "Durgapur", "O+"),
    ("Moumita Das", "1999-06-14", "Female", "9876543219", "moumita@gmail.com", "Kolkata", "A+"),
]

# 10 Rooms from HMS_aiml_22
ROOMS = [
    ("101", "General", 1, "Available", 1000.00, "Cardiology"),
    ("102", "General", 1, "Occupied", 1000.00, "Cardiology"),
    ("201", "Private", 2, "Available", 2500.00, "Neurology"),
    ("202", "Private", 2, "Occupied", 2500.00, "Neurology"),
    ("301", "ICU", 3, "Occupied", 5000.00, "Orthopedics"),
    ("302", "ICU", 3, "Available", 5000.00, "Orthopedics"),
    ("401", "General", 4, "Available", 1000.00, "Dermatology"),
    ("402", "Private", 4, "Occupied", 2500.00, "Dermatology"),
    ("501", "General", 5, "Available", 1000.00, "Pediatrics"),
    ("502", "Private", 5, "Available", 2500.00, "Pediatrics"),
]

# 10 Staff members from HMS_aiml_22
STAFF = [
    ("Ramesh Kumar", "Nurse", "9000000001", "ramesh@gmail.com", "101"),
    ("Sita Das", "Nurse", "9000000002", "sita@gmail.com", "102"),
    ("Anil Roy", "Ward Boy", "9000000003", "anil@gmail.com", "201"),
    ("Mina Ghosh", "Nurse", "9000000004", "mina@gmail.com", "202"),
    ("Raj Sen", "Receptionist", "9000000005", "raj@gmail.com", "301"),
    ("Puja Das", "Nurse", "9000000006", "puja@gmail.com", "302"),
    ("Karan Dutta", "Ward Boy", "9000000007", "karan@gmail.com", "401"),
    ("Tina Roy", "Nurse", "9000000008", "tina@gmail.com", "402"),
    ("Suman Pal", "Receptionist", "9000000009", "suman@gmail.com", "501"),
    ("Neha Sen", "Nurse", "9000000010", "neha@gmail.com", "502"),
]

# 10 Diagnostic Lab Tests from HMS_aiml_22
TESTS = [
    ("Complete Blood Count", "Blood Test", 500.00),
    ("Blood Sugar (Fasting & PP)", "Blood Test", 300.00),
    ("Lipid Profile", "Blood Test", 800.00),
    ("Urine Routine & Microscopic", "Urine Test", 250.00),
    ("X-Ray Chest (PA View)", "Imaging", 1000.00),
    ("12-Lead ECG", "Cardiac Test", 700.00),
    ("MRI Brain with Contrast", "Imaging", 5000.00),
    ("CT Scan Abdomen", "Imaging", 4000.00),
    ("Thyroid Function Test", "Blood Test", 600.00),
    ("Liver Function Test", "Blood Test", 900.00),
]

# 10 Test Results from HMS_aiml_22 (test_idx, patient_idx, value, unit, normal_range, date)
TEST_RESULTS = [
    (0, 0, "Normal", "-", "Normal", "2026-08-01"),
    (1, 1, "95", "mg/dL", "70-100", "2026-08-02"),
    (2, 2, "210", "mg/dL", "Below 200", "2026-08-03"),
    (3, 3, "Normal", "-", "Normal", "2026-08-04"),
    (4, 4, "Normal", "-", "Normal", "2026-08-05"),
    (5, 5, "Normal", "-", "Normal", "2026-08-06"),
    (6, 6, "Normal", "-", "Normal", "2026-08-07"),
    (7, 7, "Mild Abnormality", "-", "Normal", "2026-08-08"),
    (8, 8, "4.2", "mIU/L", "0.4-4.0", "2026-08-09"),
    (9, 9, "Normal", "-", "Normal", "2026-08-10"),
]

# 10 Bills & Payments from HMS_aiml_22
BILLS_DATA = [
    (0, "2026-08-01", 1500.00, 1500.00, "Paid", "Cash", "TXN001"),
    (1, "2026-08-02", 2000.00, 2000.00, "Paid", "UPI", "TXN002"),
    (2, "2026-08-03", 5000.00, 3000.00, "Partial", "Card", "TXN003"),
    (3, "2026-08-04", 1800.00, 1800.00, "Paid", "UPI", "TXN004"),
    (4, "2026-08-05", 2500.00, 1000.00, "Partial", "Cash", "TXN005"),
    (5, "2026-08-06", 1200.00, 1200.00, "Paid", "Card", "TXN006"),
    (6, "2026-08-07", 2200.00, 2200.00, "Paid", "UPI", "TXN007"),
    (7, "2026-08-08", 3500.00, 0.00, "Pending", "Cash", "TXN008"),
    (8, "2026-08-09", 1600.00, 1600.00, "Paid", "UPI", "TXN009"),
    (9, "2026-08-10", 2800.00, 1400.00, "Partial", "Card", "TXN010"),
]

# 10 Medical Records from HMS_aiml_22 (patient_idx, doctor_idx, diagnosis, prescription, treatment, notes)
MEDICAL_RECORDS = [
    (0, 0, "Viral Fever", "Paracetamol 500mg TDS", "Medication", "Rest required, drink plenty of fluids"),
    (1, 1, "Migraine", "Painkiller SOS, Sumatriptan", "Medication", "Avoid stress, ensure dark quiet room"),
    (2, 2, "Chest Pain", "Aspirin 75mg daily", "Observation", "Regular cardiac follow-up checkup"),
    (3, 3, "Skin Allergy", "Antihistamine, Cetirizine", "Medication", "Avoid contact allergens"),
    (4, 4, "Back Pain", "Pain Reliever, Muscle relaxant", "Physiotherapy", "Spinal posture exercise recommended"),
    (5, 0, "Common Cold", "Cough Syrup, Warm fluids", "Medication", "Steam inhalation twice daily"),
    (6, 1, "Chronic Migraine", "Sumatriptan 50mg", "Medication", "Adequate sleep and hydration"),
    (7, 2, "Type 2 Diabetes", "Metformin 500mg BD", "Medication", "Strict dietary sugar control"),
    (8, 3, "Seasonal Allergy", "Cetirizine 10mg nocte", "Medication", "Follow-up in 2 weeks"),
    (9, 4, "Joint Pain", "Ibuprofen 400mg TDS", "Physiotherapy", "Low impact physical exercise"),
]


def seed(conn):
    rnd = random.Random(42)
    with db.transaction(conn):
        # 1. Admin
        admin_pwd = svc.generate_password_hash("admin123")
        conn.execute("INSERT INTO admins (username, password_hash, full_name) VALUES (?,?,?)",
                     ("admin", admin_pwd, "Hospital Administrator"))

        # 2. Departments
        dept_ids = {}
        for name, loc, phone in DEPARTMENTS:
            cur = conn.execute("INSERT INTO departments (name, location, phone) VALUES (?,?,?)", (name, loc, phone))
            dept_ids[name] = cur.lastrowid

        # 3. Doctors & Schedules
        doctor_ids = []
        for name, dept, spec, phone, email, mins, days, start, end in DOCTORS:
            dept_id = dept_ids[dept]
            cur = conn.execute("INSERT INTO doctors (full_name, dept_id, specialization, phone, email, consult_minutes) "
                               "VALUES (?,?,?,?,?,?)", (name, dept_id, spec, phone, email, mins))
            doc_id = cur.lastrowid
            doctor_ids.append(doc_id)
            conn.executemany("INSERT INTO doctor_schedules (doctor_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
                             [(doc_id, d, start, end) for d in days])

        # 4. Patients (password: patient123 for all)
        patient_pwd = svc.generate_password_hash("patient123")
        patient_ids = []
        for name, dob, g, phone, email, addr, bg in PATIENTS:
            gender_code = "M" if g == "Male" else ("F" if g == "Female" else "O")
            cur = conn.execute(
                "INSERT INTO patients (full_name, date_of_birth, gender, phone, email, address, blood_group, password_hash) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (name, dob, gender_code, phone, email, addr, bg, patient_pwd))
            patient_ids.append(cur.lastrowid)

        # 5. Rooms
        room_ids = {}
        for rno, rtype, flr, st, chg, dept in ROOMS:
            cur = conn.execute(
                "INSERT INTO rooms (room_no, room_type, floor, status, daily_charge, dept_id) "
                "VALUES (?,?,?,?,?,?)",
                (rno, rtype, flr, st, chg, dept_ids.get(dept)))
            room_ids[rno] = cur.lastrowid

        # 6. Staff
        for name, role, phone, email, rno in STAFF:
            conn.execute(
                "INSERT INTO staff (full_name, role, phone, email, room_id) VALUES (?,?,?,?,?)",
                (name, role, phone, email, room_ids.get(rno)))

        # 7. Lab Tests
        test_ids = []
        for tname, ttype, cost in TESTS:
            cur = conn.execute("INSERT INTO tests (test_name, test_type, cost) VALUES (?,?,?)", (tname, ttype, cost))
            test_ids.append(cur.lastrowid)

        # 8. Test Results
        for tidx, pidx, val, unit, norm, dt in TEST_RESULTS:
            conn.execute(
                "INSERT INTO test_results (test_id, patient_id, result_value, unit, normal_range, result_date) "
                "VALUES (?,?,?,?,?,?)",
                (test_ids[tidx], patient_ids[pidx], val, unit, norm, dt))

        # 9. Bills & Payments
        for pidx, bdate, tot, paid, st, pmode, txn in BILLS_DATA:
            cur = conn.execute(
                "INSERT INTO bills (patient_id, bill_date, total_amount, amount_paid, payment_status) "
                "VALUES (?,?,?,?,?)",
                (patient_ids[pidx], bdate, tot, paid, st))
            bid = cur.lastrowid
            if paid > 0:
                conn.execute(
                    "INSERT INTO payments (bill_id, payment_date, amount, payment_mode, transaction_no) "
                    "VALUES (?,?,?,?,?)",
                    (bid, bdate, paid, pmode, txn))

        # 10. Historical Consultations & Medical Records
        for pidx, didx, diag, rx, treat, notes in MEDICAL_RECORDS:
            past_date = (svc.today() - timedelta(days=pidx + 3)).isoformat()
            slot = f"{10 + (pidx % 3):02d}:{(pidx * 15) % 60:02d}"
            cur = conn.execute(
                "INSERT INTO appointments (patient_id, doctor_id, appt_date, slot_time, status, reason) "
                "VALUES (?,?,?,?,?,?)",
                (patient_ids[pidx], doctor_ids[didx], past_date, slot, "COMPLETED", diag))
            aid = cur.lastrowid
            conn.execute(
                "INSERT INTO consultations (appointment_id, started_at, ended_at, diagnosis, prescription, treatment, notes) "
                "VALUES (?,?,?,?,?,?,?)",
                (aid, f"{past_date} {slot}:00", f"{past_date} {slot}:15", diag, rx, treat, notes))

    # 11. Today's live appointments & Queue for demonstration
    day = svc.today()
    live_appts = []
    for i, doc_id in enumerate(doctor_ids[:4]):
        slots = [s["time"] for s in svc.generate_slots(conn, doc_id, day.isoformat())][:4]
        for j, slot in enumerate(slots):
            pid = patient_ids[(i * 2 + j) % len(patient_ids)]
            cur = conn.execute(
                "INSERT INTO appointments (patient_id, doctor_id, appt_date, slot_time, status, reason) "
                "VALUES (?,?,?,?,?,?)",
                (pid, doc_id, day.isoformat(), slot, "BOOKED", "Routine checkup"))
            live_appts.append((doc_id, cur.lastrowid))

    # Check-in first 2 for each doctor to generate real queue tokens
    for doc_id, aid in live_appts[:6]:
        svc.check_in(conn, aid)

    # Call next for doctor 1 and doctor 2
    svc.call_next(conn, doctor_ids[0])
    if len(doctor_ids) > 1:
        svc.call_next(conn, doctor_ids[1])
        called = conn.execute("SELECT appointment_id FROM queue_tokens WHERE doctor_id=? AND queue_date=? AND status='CALLED'",
                              (doctor_ids[1], day.isoformat())).fetchone()
        if called:
            svc.complete_consultation(conn, called["appointment_id"], "Hypertension check", "Amlodipine 5mg", "Follow up in 1 month")
            svc.call_next(conn, doctor_ids[1])


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
    print("Seeded full HMS_aiml_22 dataset into", path)
