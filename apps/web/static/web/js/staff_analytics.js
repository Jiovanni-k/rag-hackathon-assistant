/* Staff page: summary numbers, questions per day (CSS bars), most frequent questions. */
(function () {
  "use strict";
  var t = window.I18N.t;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function setText(id, value) { document.getElementById(id).textContent = value; }

  function renderChart(perDay, days) {
    var box = document.getElementById("chart");
    box.innerHTML = "";
    if (!perDay.length) { box.appendChild(el("p", "empty", t("noData"))); return; }
    // Fill missing days with 0 so the bars are evenly spaced in time. The server groups by UTC
    // date, so the keys are built in UTC too (local dates would shift bars near midnight).
    var counts = {};
    perDay.forEach(function (d) { counts[d.date] = d.count; });
    var series = [];
    var now = new Date();
    for (var i = days - 1; i >= 0; i--) {
      var key = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - i))
        .toISOString().slice(0, 10);
      series.push({ date: key, count: counts[key] || 0 });
    }
    var max = Math.max.apply(null, series.map(function (s) { return s.count; })) || 1;
    var bars = el("div", "bars");
    series.forEach(function (s) {
      var bar = el("div", "bar");
      bar.style.height = Math.max(2, (s.count / max) * 100) + "%";
      if (!s.count) bar.style.opacity = ".25";
      bar.title = s.date + ": " + s.count;
      bars.appendChild(bar);
    });
    box.appendChild(bars);
    var axis = el("div", "bars-axis");
    axis.appendChild(el("span", "", series[0].date));
    axis.appendChild(el("span", "", series[series.length - 1].date));
    box.appendChild(axis);
  }

  async function load() {
    var days = Number(document.getElementById("days").value);
    var results = await Promise.all([
      window.API.get("/analytics/summary/?days=" + days),
      window.API.get("/analytics/top-questions/?limit=15&days=" + days)
    ]);
    var s = results[0], top = results[1];
    if (s.ok) {
      var d = s.data;
      setText("s-total", d.total_questions);
      setText("s-users", d.active_users);
      setText("s-refusal", Math.round(d.refusal_rate * 100) + "%");
      setText("s-latency", (d.avg_latency_ms / 1000).toFixed(1) + " " + t("seconds"));
      setText("s-feedback", "👍 " + d.feedback.up + "   👎 " + d.feedback.down);
      renderChart(d.questions_per_day, days);
    }
    if (top.ok) {
      var body = document.getElementById("top-body");
      body.innerHTML = "";
      var rows = top.data.results;
      document.getElementById("top-empty").hidden = rows.length > 0;
      rows.forEach(function (r, i) {
        var tr = el("tr");
        tr.appendChild(el("td", "muted", i + 1));
        var q = el("td", "", r.question);
        q.dir = "auto";
        tr.appendChild(q);
        var c = el("td");
        c.appendChild(el("span", "count-pill", r.count));
        tr.appendChild(c);
        tr.appendChild(el("td", r.refused_count ? "" : "muted", r.refused_count ? "⚠️ " + r.refused_count : "0"));
        body.appendChild(tr);
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();
    document.getElementById("days").addEventListener("change", load);
    document.addEventListener("langchange", load);
  });
})();
