import os
import sqlite3
import sys
import tempfile
import threading
import unittest
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402
import services as svc  # noqa: E402
from app import create_app  # noqa: E402
from services import AppError  # noqa: E402

TOMORROW = (svc.today() + timedelta(days=1)).isoformat()
TODAY = svc.today().isoformat()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "t.db")
        self.app = create_app({"DATABASE": self.path, "TESTING": True, "SECRET_KEY": "x"})
        self.conn = db.connect(self.path)
        c = self.conn
        c.execute("INSERT INTO departments (name) VALUES ('General')")
        c.execute("INSERT INTO doctors (full_name, dept_id, specialization, phone, email, consult_minutes) "
                  "VALUES ('Dr A', 1, 'GP', '9000000001', 'a@x.com', 15)")
        c.execute("INSERT INTO doctors (full_name, dept_id, specialization, phone, email, consult_minutes) "
                  "VALUES ('Dr B', 1, 'GP', '9000000002', 'b@x.com', 30)")
        for d in (1, 2):
            for wd in range(7):
                c.execute("INSERT INTO doctor_schedules (doctor_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
                          (d, wd, "09:00", "12:00"))
        for i in range(1, 5):
            c.execute("INSERT INTO patients (full_name, date_of_birth, gender, phone) VALUES (?,?,?,?)",
                      (f"Patient {i}", "1990-01-01", "M", f"90000001{i:02d}"))
        c.execute("INSERT INTO admins (username, password_hash, full_name) VALUES ('admin', 'x', 'Admin')")

    def tearDown(self):
        self.conn.close()

    def today_appt(self, patient, doctor, slot):
        """Insert a today's appointment directly (slot time may already be past)."""
        return self.conn.execute("INSERT INTO appointments (patient_id, doctor_id, appt_date, slot_time) VALUES (?,?,?,?)",
                                 (patient, doctor, TODAY, slot)).lastrowid


class TestBooking(Base):
    def test_book_and_double_booking_rejected(self):
        svc.book_appointment(self.conn, 1, 1, TOMORROW, "09:00")
        with self.assertRaisesRegex(AppError, "already booked"):
            svc.book_appointment(self.conn, 2, 1, TOMORROW, "09:00")

    def test_database_blocks_double_booking_even_without_app_checks(self):
        ins = "INSERT INTO appointments (patient_id, doctor_id, appt_date, slot_time) VALUES (?,?,?,?)"
        self.conn.execute(ins, (1, 1, TOMORROW, "09:15"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(ins, (2, 1, TOMORROW, "09:15"))

    def test_patient_cannot_be_in_two_places(self):
        svc.book_appointment(self.conn, 1, 1, TOMORROW, "10:00")
        with self.assertRaisesRegex(AppError, "already has an appointment"):
            svc.book_appointment(self.conn, 1, 2, TOMORROW, "10:00")

    def test_cancel_frees_slot(self):
        a = svc.book_appointment(self.conn, 1, 1, TOMORROW, "09:30")
        svc.cancel_appointment(self.conn, a)
        svc.book_appointment(self.conn, 2, 1, TOMORROW, "09:30")  # slot reusable

    def test_invalid_inputs(self):
        with self.assertRaisesRegex(AppError, "past"):
            svc.book_appointment(self.conn, 1, 1, (svc.today() - timedelta(days=1)).isoformat(), "09:00")
        with self.assertRaisesRegex(AppError, "outside"):
            svc.book_appointment(self.conn, 1, 1, TOMORROW, "09:07")      # not on a slot boundary
        with self.assertRaisesRegex(AppError, "outside"):
            svc.book_appointment(self.conn, 1, 1, TOMORROW, "12:00")      # after hours
        with self.assertRaisesRegex(AppError, "at most"):
            svc.book_appointment(self.conn, 1, 1, (svc.today() + timedelta(days=90)).isoformat(), "09:00")
        with self.assertRaisesRegex(AppError, "valid date"):
            svc.book_appointment(self.conn, 1, 1, "31-12-2030", "09:00")

    def test_reschedule(self):
        a = svc.book_appointment(self.conn, 1, 1, TOMORROW, "09:00")
        b = svc.book_appointment(self.conn, 2, 1, TOMORROW, "09:15")
        with self.assertRaisesRegex(AppError, "already booked"):
            svc.reschedule_appointment(self.conn, a, TOMORROW, "09:15")
        svc.reschedule_appointment(self.conn, a, TOMORROW, "09:45")
        row = self.conn.execute("SELECT slot_time FROM appointments WHERE appointment_id=?", (a,)).fetchone()
        self.assertEqual(row["slot_time"], "09:45")
        svc.book_appointment(self.conn, 3, 1, TOMORROW, "09:00")           # old slot is free again
        self.assertIsNotNone(b)

    def test_failed_booking_leaves_no_partial_data(self):
        with self.assertRaises(AppError):
            svc.book_appointment(self.conn, 999, 1, TOMORROW, "09:00")     # unknown patient
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0], 0)
        self.assertFalse(self.conn.in_transaction)

    def test_concurrent_booking_only_one_wins(self):
        results = []

        def attempt(pid):
            conn = db.connect(self.path)
            try:
                svc.book_appointment(conn, pid, 1, TOMORROW, "11:00")
                results.append("ok")
            except AppError:
                results.append("rejected")
            finally:
                conn.close()

        threads = [threading.Thread(target=attempt, args=(p,)) for p in (1, 2, 3, 4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(results), ["ok", "rejected", "rejected", "rejected"])

    def test_foreign_keys_enforced(self):
        svc.book_appointment(self.conn, 1, 1, TOMORROW, "09:00")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM patients WHERE patient_id = 1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO appointments (patient_id, doctor_id, appt_date, slot_time) "
                              "VALUES (99, 1, ?, '10:00')", (TOMORROW,))


class TestHistory(Base):
    def test_triggers_log_and_are_append_only(self):
        a = svc.book_appointment(self.conn, 1, 1, TOMORROW, "09:00")
        svc.reschedule_appointment(self.conn, a, TOMORROW, "09:30")
        svc.cancel_appointment(self.conn, a)
        actions = [r["action"] for r in svc.history_log(self.conn, a)][::-1]
        self.assertEqual(actions, ["BOOKED", "RESCHEDULED", "CANCELLED"])
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute("DELETE FROM appointment_history")
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute("UPDATE appointment_history SET action='X'")


class TestQueue(Base):
    def test_tokens_positions_and_flow(self):
        ids = [self.today_appt(p, 1, f"09:{15 * (p - 1):02d}") for p in (1, 2, 3)]
        self.assertEqual([svc.check_in(self.conn, i) for i in ids], [1, 2, 3])
        with self.assertRaisesRegex(AppError, "Booked"):
            svc.check_in(self.conn, ids[0])                                # no double check-in
        rows = {r["token_no"]: r for r in self.conn.execute("SELECT * FROM v_queue ORDER BY token_no")}
        self.assertEqual((rows[1]["people_ahead"], rows[3]["people_ahead"]), (0, 2))
        self.assertEqual(rows[3]["est_wait_min"], 30)                      # 2 ahead x 15 min

        self.assertEqual(svc.call_next(self.conn, 1), 1)
        with self.assertRaisesRegex(AppError, "Finish the current"):
            svc.call_next(self.conn, 1)                                    # one patient at a time
        svc.complete_consultation(self.conn, ids[0], "Flu", "Rest", "")
        self.assertEqual(svc.call_next(self.conn, 1), 2)
        svc.complete_consultation(self.conn, ids[1])
        # token 3 now has nobody ahead
        r = self.conn.execute("SELECT people_ahead FROM v_queue WHERE token_no = 3").fetchone()
        self.assertEqual(r["people_ahead"], 0)
        hist = svc.patient_history(self.conn, 1)
        self.assertEqual(hist[0]["diagnosis"], "Flu")

    def test_token_numbers_are_per_doctor(self):
        a = self.today_appt(1, 1, "09:00")
        b = self.today_appt(2, 2, "09:00")
        self.assertEqual((svc.check_in(self.conn, a), svc.check_in(self.conn, b)), (1, 1))

    def test_cancel_and_skip_update_positions(self):
        ids = [self.today_appt(p, 1, f"09:{15 * (p - 1):02d}") for p in (1, 2, 3)]
        for i in ids:
            svc.check_in(self.conn, i)
        svc.cancel_appointment(self.conn, ids[0])
        svc.skip_patient(self.conn, ids[1])
        r = self.conn.execute("SELECT people_ahead FROM v_queue WHERE token_no = 3").fetchone()
        self.assertEqual(r["people_ahead"], 0)
        st = self.conn.execute("SELECT status FROM appointments WHERE appointment_id=?", (ids[1],)).fetchone()[0]
        self.assertEqual(st, "NO_SHOW")

    def test_checkin_only_today(self):
        a = svc.book_appointment(self.conn, 1, 1, TOMORROW, "09:00")
        with self.assertRaisesRegex(AppError, "day of the appointment"):
            svc.check_in(self.conn, a)

    def test_db_allows_single_called_token(self):
        ids = [self.today_appt(p, 1, f"09:{15 * (p - 1):02d}") for p in (1, 2)]
        for i in ids:
            svc.check_in(self.conn, i)
        self.conn.execute("UPDATE queue_tokens SET status='CALLED' WHERE token_no=1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE queue_tokens SET status='CALLED' WHERE token_no=2")


class TestRegistration(Base):
    def test_patient_validation_and_unique_phone(self):
        good = {"full_name": "New Person", "date_of_birth": "2000-05-05", "gender": "F", "phone": "9123456789"}
        svc.add_patient(self.conn, good)
        with self.assertRaisesRegex(AppError, "already registered"):
            svc.add_patient(self.conn, good)
        with self.assertRaisesRegex(AppError, "phone"):
            svc.add_patient(self.conn, {**good, "phone": "12345"})
        with self.assertRaisesRegex(AppError, "future"):
            svc.add_patient(self.conn, {**good, "phone": "9123456780", "date_of_birth": "2999-01-01"})

    def test_doctor_registration(self):
        form = {"full_name": "Dr New", "dept_id": "1", "specialization": "ENT", "phone": "9555555555",
                "email": "new@x.com", "consult_minutes": "20", "start_time": "10:00", "end_time": "12:00"}
        did = svc.add_doctor(self.conn, form, ["0", "1"])
        slots = svc.generate_slots(self.conn, did, self._next_weekday(0))
        self.assertEqual([s["time"] for s in slots], ["10:00", "10:20", "10:40", "11:00", "11:20", "11:40"])
        with self.assertRaisesRegex(AppError, "already registered"):
            svc.add_doctor(self.conn, {**form, "email": "other@x.com"}, ["0"])
        with self.assertRaisesRegex(AppError, "working day"):
            svc.add_doctor(self.conn, {**form, "phone": "9555555556", "email": "o2@x.com"}, [])

    @staticmethod
    def _next_weekday(wd):
        d = svc.today() + timedelta(days=1)
        while d.weekday() != wd:
            d += timedelta(days=1)
        return d.isoformat()


class TestWeb(Base):
    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()
        with self.client.session_transaction() as s:
            s["csrf"] = "tok"
            s["user"] = {"role": "admin", "admin_id": 1, "username": "admin", "name": "Admin"}

    def post(self, url, **data):
        return self.client.post(url, data={"csrf_token": "tok", **data}, follow_redirects=True)

    def test_pages_render(self):
        for url in ["/", "/queue", "/queue/partial", "/patients", "/patients/1", "/doctors", "/doctors/new",
                    "/patients/new", "/appointments", "/appointments/book", "/history"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get("/patients/999").status_code, 404)

    def test_csrf_required(self):
        self.assertEqual(self.client.post("/appointments/book", data={}).status_code, 400)

    def test_book_via_form_and_api(self):
        r = self.post("/appointments/book", patient_id="1", doctor_id="1", appt_date=TOMORROW, slot_time="09:00", reason="x")
        self.assertIn(b"Appointment booked", r.data)
        r = self.post("/appointments/book", patient_id="2", doctor_id="1", appt_date=TOMORROW, slot_time="09:00")
        self.assertIn(b"already booked", r.data)
        j = self.client.get(f"/api/slots?doctor_id=1&date={TOMORROW}").get_json()
        self.assertFalse(next(s for s in j["slots"] if s["time"] == "09:00")["available"])
        self.assertEqual(self.client.get("/api/slots?doctor_id=abc&date=x").status_code, 400)

    def test_xss_is_escaped(self):
        self.post("/patients/new", full_name="<script>alert(1)</script>", date_of_birth="1990-01-01", gender="M", phone="9876500000")
        html = self.client.get("/patients").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_queue_actions_over_http(self):
        a = self.today_appt(1, 1, "09:00")
        self.assertIn(b"Token number #1", self.post(f"/appointments/{a}/checkin").data)
        self.assertIn(b"Token #1 called", self.post("/queue/call/1").data)
        self.assertIn(b"Consultation completed", self.post(f"/queue/complete/{a}", diagnosis="ok").data)


class TestAuth(Base):
    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()

    def test_unauthenticated_redirect(self):
        r = self.client.get("/", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_admin_login(self):
        svc.add_admin(self.conn, "chief", "chief123", "Chief Doctor")
        with self.client.session_transaction() as s:
            s["csrf"] = "tok"
        r = self.client.post("/login", data={"csrf_token": "tok", "role": "admin", "username": "chief", "password": "chief123"}, follow_redirects=True)
        self.assertIn(b"Welcome back, Chief Doctor", r.data)

    def test_patient_registration_and_portal(self):
        with self.client.session_transaction() as s:
            s["csrf"] = "tok"
        r = self.client.post("/register", data={
            "csrf_token": "tok",
            "full_name": "Portal Patient",
            "date_of_birth": "1995-02-14",
            "gender": "F",
            "phone": "9888877777",
            "email": "portal@test.com",
            "password": "secretpassword",
            "confirm_password": "secretpassword"
        }, follow_redirects=True)
        self.assertIn(b"Welcome to your patient portal", r.data)
        self.assertIn(b"Portal Patient", r.data)

    def test_patient_access_restriction(self):
        # Patient session
        with self.client.session_transaction() as s:
            s["csrf"] = "tok"
            s["user"] = {"role": "patient", "patient_id": 1, "name": "Patient 1", "phone": "9000000101"}

        # Attempt to access admin routes
        for url in ["/patients", "/queue", "/history", "/doctors/new"]:
            r = self.client.get(url, follow_redirects=True)
            self.assertIn(b"Access denied", r.data)

        # Access patient allowed pages
        r = self.client.get("/portal")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/doctors")
        self.assertEqual(r.status_code, 200)

    def test_patient_cannot_tamper_other_patient_appointment(self):
        a1 = svc.book_appointment(self.conn, 1, 1, TOMORROW, "09:00")
        a2 = svc.book_appointment(self.conn, 2, 1, TOMORROW, "09:15")

        # Logged in as Patient 1
        with self.client.session_transaction() as s:
            s["csrf"] = "tok"
            s["user"] = {"role": "patient", "patient_id": 1, "name": "Patient 1", "phone": "9000000101"}

        # Try to reschedule Patient 2's appointment
        r = self.client.post(f"/appointments/{a2}/reschedule", data={"csrf_token": "tok", "appt_date": TOMORROW, "slot_time": "09:30"}, follow_redirects=True)
        self.assertIn(b"You can only reschedule your own appointments", r.data)

        # Try to cancel Patient 2's appointment
        r = self.client.post(f"/appointments/{a2}/cancel", data={"csrf_token": "tok"}, follow_redirects=True)
        self.assertIn(b"You can only cancel your own appointments", r.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
