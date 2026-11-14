/* Staff page: list documents, upload (indexed in the background), delete, full re-index. */
(function () {
  "use strict";
  var t = window.I18N.t;
  var pollTimer = null;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function fmtDate(iso) {
    try {
      return new Date(iso).toLocaleDateString(window.I18N.lang() === "ar" ? "ar" : "en",
        { year: "numeric", month: "short", day: "numeric" });
    } catch (e) { return iso; }
  }

  function message(text, ok) {
    var box = document.getElementById("upload-msg");
    box.hidden = false;
    box.className = "alert " + (ok ? "alert-ok" : "alert-error");
    box.textContent = text;
  }

  async function loadHealth() {
    var res = await window.API.get("/health/");
    var dot = document.getElementById("health-dot");
    var text = document.getElementById("health-text");
    if (!res.ok) { dot.className = "status-dot warn"; text.textContent = "?"; return false; }
    var h = res.data;
    dot.className = "status-dot " + (h.reindexing ? "warn" : h.status === "ok" ? "ok" : "warn");
    text.textContent = h.reindexing ? t("reindexing")
      : h.documents + " " + t("documentsCount") + " · " + h.chunks + " " + t("chunks");
    document.getElementById("reindex").disabled = h.reindexing;
    return h.reindexing;
  }

  async function loadDocs() {
    var res = await window.API.getAll("/documents/");
    if (!res.ok) return false;
    var body = document.getElementById("docs-body");
    body.innerHTML = "";
    var docs = res.data.results;
    document.getElementById("docs-empty").hidden = docs.length > 0;
    var processing = false;
    docs.forEach(function (d) {
      processing = processing || d.status === "processing";
      var tr = el("tr");
      var title = el("td", "", d.title);
      title.dir = "auto";
      tr.appendChild(title);
      var file = el("td", "muted small", d.filename);
      file.dir = "ltr";
      tr.appendChild(file);
      tr.appendChild(el("td", "", d.version_year || "—"));
      var st = el("td");
      var badge = el("span", "badge badge-" + d.status, t(d.status));
      if (d.error) badge.title = d.error;
      st.appendChild(badge);
      tr.appendChild(st);
      tr.appendChild(el("td", "", d.status === "ready" ? d.chunk_count : "—"));
      tr.appendChild(el("td", "muted small", fmtDate(d.uploaded_at)));
      var act = el("td");
      var del = el("button", "btn btn-danger", t("remove"));
      del.type = "button";
      del.addEventListener("click", async function () {
        if (!window.confirm(t("confirmDocDelete"))) return;
        var r = await window.API.del("/documents/" + d.id + "/");
        if (!r.ok) { message(window.API.friendlyError(r), false); return; }
        refresh();
      });
      act.appendChild(del);
      tr.appendChild(act);
      body.appendChild(tr);
    });
    return processing;
  }

  async function refresh() {
    var busy = await Promise.all([loadDocs(), loadHealth()]);
    clearTimeout(pollTimer);
    if (busy[0] || busy[1]) pollTimer = setTimeout(refresh, 3000);   // poll while indexing
  }

  document.addEventListener("DOMContentLoaded", function () {
    refresh();

    document.getElementById("upload-form").addEventListener("submit", async function (e) {
      e.preventDefault();
      var form = e.target;
      var btn = form.querySelector("button[type=submit]");
      var data = new FormData(form);
      if (!data.get("version_year")) data.delete("version_year");
      btn.disabled = true;
      var res = await window.API.post("/documents/", data, { timeout: 180000 });
      btn.disabled = false;
      if (!res.ok) { message(window.API.friendlyError(res), false); return; }
      form.reset();
      message(t("uploaded"), true);
      refresh();
    });

    document.getElementById("reindex").addEventListener("click", async function () {
      if (!window.confirm(t("reindexConfirm"))) return;
      var res = await window.API.post("/documents/reindex/");
      if (!res.ok) { message(window.API.friendlyError(res), false); return; }
      refresh();
    });

    document.addEventListener("langchange", refresh);
  });
})();
