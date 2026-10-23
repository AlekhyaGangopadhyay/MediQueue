(function () {
  // ---- Slot picker (book + reschedule pages) --------------------------------
  var picker = document.querySelector("[data-slot-picker]");
  if (picker) {
    var form = document.getElementById("book-form");
    var doctorSel = form.querySelector("[name=doctor_id]");
    var dateInput = form.querySelector("[name=appt_date]");
    var selected = picker.dataset.selected || "";

    function esc(s) { var d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

    function load() {
      var doctor = picker.dataset.doctor || (doctorSel && doctorSel.value);
      if (!doctor || !dateInput.value) {
        picker.innerHTML = '<p class="muted">Choose a doctor and date to see free slots.</p>';
        return;
      }
      var url = "/api/slots?doctor_id=" + encodeURIComponent(doctor) + "&date=" + encodeURIComponent(dateInput.value);
      if (picker.dataset.exclude) url += "&exclude=" + encodeURIComponent(picker.dataset.exclude);
      fetch(url).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
        .then(function (res) {
          if (!res.ok) { picker.innerHTML = '<p class="muted">' + esc(res.j.error || "Could not load slots.") + "</p>"; return; }
          var slots = res.j.slots;
          if (!slots.length) { picker.innerHTML = '<p class="muted">The doctor does not work on this date.</p>'; return; }
          if (!slots.some(function (s) { return s.available; })) {
            picker.innerHTML = '<p class="muted">All slots on this date are taken or have passed.</p>'; return;
          }
          picker.innerHTML = slots.map(function (s) {
            return '<label class="slot' + (s.available ? "" : " off") + '"><input type="radio" name="slot_time" value="' + s.time + '"' +
              (s.available ? "" : " disabled") + (s.time === selected ? " checked" : "") + " required><span>" + s.time + "</span></label>";
          }).join("");
        })
        .catch(function () { picker.innerHTML = '<p class="muted">Could not load slots. Check your connection.</p>'; });
    }
    if (doctorSel) doctorSel.addEventListener("change", function () { selected = ""; load(); });
    dateInput.addEventListener("change", function () { selected = ""; load(); });
    load();
  }

  // ---- Live queue auto-refresh ----------------------------------------------
  var root = document.getElementById("queue-root");
  if (root) {
    setInterval(function () {
      // Don't wipe a half-typed consultation note.
      if (root.querySelector("details[open]") || root.contains(document.activeElement) &&
          /INPUT|TEXTAREA/.test(document.activeElement.tagName)) return;
      fetch("/queue/partial").then(function (r) { return r.ok ? r.text() : null; })
        .then(function (html) { if (html) root.innerHTML = html; }).catch(function () {});
    }, 10000);
  }
})();
