"""Hospital Appointment & Queue Management System - Flask application."""
import os
import secrets
from datetime import timedelta

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import db
import services as svc
from services import AppError

STATUS_LABEL = {
    "BOOKED": "Booked", "CHECKED_IN": "Waiting", "IN_CONSULTATION": "In consultation",
    "COMPLETED": "Completed", "CANCELLED": "Cancelled", "NO_SHOW": "No-show",
    "WAITING": "Waiting", "CALLED": "Now serving", "DONE": "Done", "SKIPPED": "Skipped",
    "RESCHEDULED": "Rescheduled",
}


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.path.join(app.instance_path, "hospital.db"),
    )
    if config:
        app.config.update(config)
    os.makedirs(os.path.dirname(app.config["DATABASE"]) or ".", exist_ok=True)
    app.teardown_appcontext(db.close_db)

    # Ensure database schema, tables, columns, views, and seed data exist
    boot = db.connect(app.config["DATABASE"])
    db.ensure_schema(boot, auto_seed=not app.config.get("TESTING"))
    boot.close()

    # ---------------------------------------------------------- Auth & Sessions
    def current_user():
        return session.get("user")

    def is_admin():
        u = current_user()
        return bool(u and u.get("role") == "admin")

    def is_patient():
        u = current_user()
        return bool(u and u.get("role") == "patient")

    def require_login():
        if not current_user():
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login", next=request.full_path))
        return None

    def require_admin():
        req = require_login()
        if req:
            return req
        if not is_admin():
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("patient_portal"))
        return None

    def require_patient():
        req = require_login()
        if req:
            return req
        if not is_patient() or not current_user().get("patient_id"):
            session.pop("user", None)
            flash("Please sign in with a patient account.", "error")
            return redirect(url_for("login"))
        return None

    # ---------------------------------------------------------- CSRF & Globals
    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    app.jinja_env.globals.update(
        csrf_token=csrf_token,
        current_user=current_user,
        is_admin=is_admin,
        is_patient=is_patient,
        status_label=lambda s: STATUS_LABEL.get(s, s),
        today=lambda: svc.today().isoformat(),
        max_date=lambda: (svc.today() + timedelta(days=svc.MAX_ADVANCE_DAYS)).isoformat(),
        WEEKDAYS=svc.WEEKDAYS
    )

    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            expected = session.get("csrf")
            sent = request.form.get("csrf_token", "")
            if not expected or not secrets.compare_digest(expected, sent):
                abort(400, "Invalid or missing CSRF token. Reload the page and try again.")

    def back(default):
        nxt = request.form.get("next", "")
        return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else default)

    def run(action, success, default_next, *args, **kwargs):
        """Run a service call; flash success/error; redirect."""
        try:
            result = action(db.get_db(), *args, **kwargs)
            flash(success(result) if callable(success) else success, "ok")
        except AppError as exc:
            flash(str(exc), "error")
        return back(default_next)

    # ---------------------------------------------------------- Authentication
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user():
            return redirect(url_for("dashboard") if is_admin() else url_for("patient_portal"))

        if request.method == "POST":
            role = request.form.get("role", "patient")
            conn = db.get_db()
            if role == "admin":
                username = request.form.get("username", "")
                password = request.form.get("password", "")
                admin = svc.authenticate_admin(conn, username, password)
                if admin:
                    session["user"] = {
                        "role": "admin",
                        "admin_id": admin["admin_id"],
                        "username": admin["username"],
                        "name": admin["full_name"]
                    }
                    flash(f"Welcome back, {admin['full_name']}!", "ok")
                    nxt = request.args.get("next") or request.form.get("next")
                    return redirect(nxt if nxt and nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
                flash("Invalid admin username or password.", "error")
            else:
                identifier = request.form.get("identifier", "")
                password = request.form.get("password", "")
                patient = svc.authenticate_patient(conn, identifier, password)
                if patient:
                    session["user"] = {
                        "role": "patient",
                        "patient_id": patient["patient_id"],
                        "name": patient["full_name"],
                        "phone": patient["phone"]
                    }
                    flash(f"Welcome back, {patient['full_name']}!", "ok")
                    nxt = request.args.get("next") or request.form.get("next")
                    return redirect(nxt if nxt and nxt.startswith("/") and not nxt.startswith("//") else url_for("patient_portal"))
                flash("Invalid phone/email or password.", "error")

        return render_template("login.html", next=request.args.get("next", ""))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user():
            return redirect(url_for("dashboard") if is_admin() else url_for("patient_portal"))

        if request.method == "POST":
            f = request.form
            pwd = f.get("password", "")
            confirm = f.get("confirm_password", "")
            if pwd != confirm:
                flash("Passwords do not match.", "error")
                return render_template("register.html", f=f)
            try:
                conn = db.get_db()
                pid = svc.add_patient(conn, f, password=pwd)
                session["user"] = {
                    "role": "patient",
                    "patient_id": pid,
                    "name": f.get("full_name"),
                    "phone": f.get("phone")
                }
                flash("Registration successful! Welcome to your patient portal.", "ok")
                return redirect(url_for("patient_portal"))
            except AppError as exc:
                flash(str(exc), "error")
                return render_template("register.html", f=f)

        return render_template("register.html", f={})

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        session.pop("user", None)
        flash("You have been signed out.", "ok")
        return redirect(url_for("login"))

    # ---------------------------------------------------------- Patient Portal
    @app.get("/portal")
    def patient_portal():
        req = require_patient()
        if req:
            return req
        pid = current_user().get("patient_id")
        try:
            data = svc.patient_portal_data(db.get_db(), pid)
        except AppError:
            session.pop("user", None)
            flash("Your patient profile was not found in the active database. Please sign in or register.", "error")
            return redirect(url_for("login"))
        except Exception as exc:
            app.logger.exception("Error loading portal: %s", exc)
            flash("Unable to load patient records. Please try again.", "error")
            return redirect(url_for("lab_tests"))
        return render_template("patient_portal.html", data=data, page="portal")

    # ---------------------------------------------------------- Dashboard (Admin)
    @app.get("/")
    def dashboard():
        if not current_user():
            return redirect(url_for("login"))
        if is_patient():
            return redirect(url_for("patient_portal"))
        return render_template("dashboard.html", s=svc.dashboard_stats(db.get_db()),
                               board=svc.queue_board(db.get_db()), page="dashboard")

    # ---------------------------------------------------------- Patients (Admin)
    @app.get("/patients")
    def patients():
        req = require_admin()
        if req:
            return req
        q = request.args.get("q", "")
        return render_template("patients.html", rows=svc.list_patients(db.get_db(), q), q=q, page="patients")

    @app.route("/patients/new", methods=["GET", "POST"])
    def patient_new():
        req = require_admin()
        if req:
            return req
        if request.method == "POST":
            try:
                pid = svc.add_patient(db.get_db(), request.form)
                flash("Patient registered successfully.", "ok")
                return redirect(url_for("patient_detail", pid=pid))
            except AppError as exc:
                flash(str(exc), "error")
        return render_template("patient_form.html", f=request.form, page="patients")

    @app.get("/patients/<int:pid>")
    def patient_detail(pid):
        req = require_admin()
        if req:
            return req
        conn = db.get_db()
        try:
            p = svc.get_patient(conn, pid)
        except AppError:
            abort(404)
        return render_template("patient_detail.html", p=p,
                               hist=svc.patient_history(conn, pid),
                               bills=svc.list_bills(conn, pid),
                               tests=svc.list_test_results(conn, pid),
                               page="patients")

    # ---------------------------------------------------------- Rooms & Wards (HMS_aiml_22)
    @app.get("/rooms")
    def rooms():
        req = require_login()
        if req:
            return req
        return render_template("rooms.html", rows=svc.list_rooms(db.get_db()), page="rooms")

    # ---------------------------------------------------------- Staff Directory (HMS_aiml_22)
    @app.get("/staff")
    def staff():
        req = require_admin()
        if req:
            return req
        return render_template("staff.html", rows=svc.list_staff(db.get_db()), page="staff")

    # ---------------------------------------------------------- Billing & Payments (HMS_aiml_22)
    @app.get("/billing")
    def billing():
        req = require_admin()
        if req:
            return req
        return render_template("billing.html", rows=svc.list_bills(db.get_db()), page="billing")

    # ---------------------------------------------------------- Laboratory & Tests (HMS_aiml_22)
    @app.get("/tests")
    def lab_tests():
        req = require_login()
        if req:
            return req
        conn = db.get_db()
        tests = svc.list_tests(conn)
        my_bookings = svc.list_test_bookings(conn, patient_id=current_user()["patient_id"]) if is_patient() else []
        all_bookings = svc.list_test_bookings(conn) if is_admin() else []
        results = svc.list_test_results(conn) if is_admin() else []
        return render_template("tests.html", tests=tests, my_bookings=my_bookings,
                               all_bookings=all_bookings, results=results, page="tests")

    @app.route("/tests/book", methods=["GET", "POST"])
    def test_book():
        req = require_login()
        if req:
            return req
        conn = db.get_db()
        tests = svc.list_tests(conn)
        slots = ["07:30", "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "15:00", "16:00", "17:00"]
        patients = svc.list_patients(conn) if is_admin() else []
        selected_test_id = request.args.get("test_id")
        try:
            selected_test_id = int(selected_test_id) if selected_test_id else None
        except ValueError:
            selected_test_id = None

        if request.method == "POST":
            pid = current_user()["patient_id"] if is_patient() else None
            try:
                bid = svc.book_test(conn, request.form, patient_id=pid)
                flash("Diagnostic test booked successfully! Our lab team will be ready for your sample collection.", "ok")
                return redirect(url_for("lab_tests"))
            except AppError as exc:
                flash(str(exc), "error")

        return render_template(
            "test_book.html",
            tests=tests,
            slots=slots,
            patients=patients,
            selected_test_id=selected_test_id,
            today=svc.today().isoformat(),
            page="tests"
        )

    @app.post("/tests/bookings/<int:bid>/cancel")
    def test_booking_cancel(bid):
        req = require_login()
        if req:
            return req
        conn = db.get_db()
        pid = current_user()["patient_id"] if is_patient() else None
        try:
            svc.cancel_test_booking(conn, bid, patient_id=pid)
            flash("Diagnostic test booking cancelled.", "ok")
        except AppError as exc:
            flash(str(exc), "error")
        return redirect(url_for("lab_tests"))

    @app.post("/tests/bookings/<int:bid>/complete")
    def test_booking_complete(bid):
        req = require_admin()
        if req:
            return req
        conn = db.get_db()
        try:
            svc.complete_test_booking(conn, bid)
            flash("Diagnostic test marked as completed.", "ok")
        except AppError as exc:
            flash(str(exc), "error")
        return redirect(url_for("lab_tests"))

    # ---------------------------------------------------------- Doctors (All logged-in)
    @app.get("/doctors")
    def doctors():
        req = require_login()
        if req:
            return req
        return render_template("doctors.html", rows=svc.list_doctors(db.get_db()), page="doctors")

    @app.route("/doctors/new", methods=["GET", "POST"])
    def doctor_new():
        req = require_admin()
        if req:
            return req
        conn = db.get_db()
        if request.method == "POST":
            try:
                svc.add_doctor(conn, request.form, request.form.getlist("weekdays"))
                flash("Doctor registered successfully.", "ok")
                return redirect(url_for("doctors"))
            except AppError as exc:
                flash(str(exc), "error")
        return render_template("doctor_form.html", f=request.form, depts=svc.list_departments(conn),
                               chosen=request.form.getlist("weekdays"), page="doctors")

    # ---------------------------------------------------------- Appointments
    @app.get("/appointments")
    def appointments():
        req = require_admin()
        if req:
            return req
        conn, a = db.get_db(), request.args
        try:
            rows = svc.list_appointments(conn, a.get("date", ""), a.get("doctor_id", ""),
                                         a.get("status", ""), a.get("q", ""))
        except AppError as exc:
            flash(str(exc), "error")
            rows = []
        return render_template("appointments.html", rows=rows, f=a, doctors=svc.list_doctors(conn),
                               statuses=list(STATUS_LABEL)[:6], page="appointments")

    @app.route("/appointments/book", methods=["GET", "POST"])
    def appointment_book():
        req = require_login()
        if req:
            return req
        conn = db.get_db()
        if request.method == "POST":
            f = request.form
            try:
                if is_patient():
                    patient_id = current_user()["patient_id"]
                else:
                    if not f.get("patient_id", "").isdigit():
                        raise AppError("Select a patient.")
                    patient_id = int(f["patient_id"])

                if not f.get("doctor_id", "").isdigit():
                    raise AppError("Select a doctor.")
                if not f.get("slot_time"):
                    raise AppError("Select a time slot.")

                svc.book_appointment(conn, patient_id, int(f["doctor_id"]),
                                     f.get("appt_date", ""), f["slot_time"], f.get("reason", ""))
                flash("Appointment booked successfully.", "ok")
                if is_patient():
                    return redirect(url_for("patient_portal"))
                return redirect(url_for("appointments", date=f.get("appt_date")))
            except AppError as exc:
                flash(str(exc), "error")

        form = request.form if request.method == "POST" else request.args
        patients = [] if is_patient() else svc.list_patients(conn)
        return render_template("book.html", f=form, patients=patients,
                               doctors=svc.list_doctors(conn, active_only=True), page="book")

    @app.route("/appointments/<int:aid>/reschedule", methods=["GET", "POST"])
    def appointment_reschedule(aid):
        req = require_login()
        if req:
            return req
        conn = db.get_db()
        try:
            appt = svc.get_appointment_detail(conn, aid)
        except AppError:
            abort(404)

        if is_patient() and appt["patient_id"] != current_user()["patient_id"]:
            flash("You can only reschedule your own appointments.", "error")
            return redirect(url_for("patient_portal"))

        if request.method == "POST":
            try:
                svc.reschedule_appointment(conn, aid, request.form.get("appt_date", ""),
                                           request.form.get("slot_time", ""))
                flash("Appointment rescheduled successfully.", "ok")
                if is_patient():
                    return redirect(url_for("patient_portal"))
                return redirect(url_for("appointments", date=request.form.get("appt_date")))
            except AppError as exc:
                flash(str(exc), "error")

        return render_template("reschedule.html", a=appt, page="appointments")

    @app.post("/appointments/<int:aid>/cancel")
    def appointment_cancel(aid):
        req = require_login()
        if req:
            return req
        conn = db.get_db()
        try:
            appt = svc.get_appointment_detail(conn, aid)
        except AppError:
            abort(404)

        if is_patient() and appt["patient_id"] != current_user()["patient_id"]:
            flash("You can only cancel your own appointments.", "error")
            return redirect(url_for("patient_portal"))

        next_page = url_for("patient_portal") if is_patient() else url_for("appointments")
        return run(svc.cancel_appointment, "Appointment cancelled.", next_page, aid)

    @app.post("/appointments/<int:aid>/checkin")
    def appointment_checkin(aid):
        req = require_login()
        if req:
            return req
        conn = db.get_db()
        try:
            appt = svc.get_appointment_detail(conn, aid)
        except AppError:
            abort(404)

        if is_patient() and appt["patient_id"] != current_user()["patient_id"]:
            flash("You can only check in for your own appointments.", "error")
            return redirect(url_for("patient_portal"))

        next_page = url_for("patient_portal") if is_patient() else url_for("queue")
        return run(svc.check_in, lambda n: f"Checked in. Token number #{n} issued.", next_page, aid)

    # ---------------------------------------------------------- Queue (Admin / Reception)
    @app.get("/queue")
    def queue():
        req = require_admin()
        if req:
            return req
        return render_template("queue.html", board=svc.queue_board(db.get_db()), page="queue")

    @app.get("/queue/partial")
    def queue_partial():
        req = require_admin()
        if req:
            return req
        return render_template("_queue_board.html", board=svc.queue_board(db.get_db()))

    @app.post("/queue/call/<int:doctor_id>")
    def queue_call(doctor_id):
        req = require_admin()
        if req:
            return req
        return run(svc.call_next, lambda n: f"Token #{n} called into consultation.", url_for("queue"), doctor_id)

    @app.post("/queue/complete/<int:aid>")
    def queue_complete(aid):
        req = require_admin()
        if req:
            return req
        f = request.form
        return run(svc.complete_consultation, "Consultation completed and saved.", url_for("queue"), aid,
                   f.get("diagnosis", ""), f.get("prescription", ""), f.get("notes", ""))

    @app.post("/queue/skip/<int:aid>")
    def queue_skip(aid):
        req = require_admin()
        if req:
            return req
        return run(svc.skip_patient, "Patient marked as no-show and skipped.", url_for("queue"), aid)

    # ---------------------------------------------------------- History / Slot API
    @app.get("/history")
    def history():
        req = require_admin()
        if req:
            return req
        aid = request.args.get("appointment_id", "")
        rows = svc.history_log(db.get_db(), int(aid) if aid.isdigit() else None)
        return render_template("history.html", rows=rows, page="history")

    @app.get("/api/slots")
    def api_slots():
        try:
            doctor_id = int(request.args.get("doctor_id", ""))
            exclude = request.args.get("exclude")
            slots = svc.generate_slots(db.get_db(), doctor_id, request.args.get("date", ""),
                                       int(exclude) if exclude and exclude.isdigit() else None)
        except (ValueError, AppError) as exc:
            return jsonify(error=str(exc) if isinstance(exc, AppError) else "Invalid doctor."), 400
        return jsonify(slots=slots)

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Internal Server Error: %s", error)
        return render_template("500.html", error=error), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="0.0.0.0", port=port)
