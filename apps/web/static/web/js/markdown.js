/* Minimal, safe markdown for answers: everything is HTML-escaped first, then we add
   paragraphs, headings, ordered/unordered lists, tables, **bold**, *italic*, `code`,
   and citation markers like [1] or [2, 3]. Each block gets dir="auto" for mixed AR/EN text. */
(function () {
  "use strict";

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function inline(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
      .replace(/\[(\d+(?:\s*[,،]\s*\d+)*)\]/g, function (_, nums) {
        return '<sup class="cite">[' + nums.replace(/\s+/g, "") + "]</sup>";
      });
  }

  var OL = /^\s*(\d+)[.)]\s+(.*)$/;
  var UL = /^\s*[-*•]\s+(.*)$/;
  var HEADING = /^\s*(#{1,4})\s+(.*)$/;
  var TABLE_ROW = /^\s*\|.*\|\s*$/;
  var TABLE_SEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

  function cells(row) {
    return row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(function (c) { return c.trim(); });
  }

  function render(text) {
    var lines = String(text || "").replace(/\r\n?/g, "\n").split("\n");
    var out = [], para = [], i = 0;

    function flushPara() {
      if (para.length) out.push('<p dir="auto">' + para.map(inline).join("<br>") + "</p>");
      para = [];
    }

    while (i < lines.length) {
      var line = lines[i];
      if (!line.trim()) { flushPara(); i++; continue; }

      if (TABLE_ROW.test(line) && i + 1 < lines.length && TABLE_SEP.test(lines[i + 1])) {
        flushPara();
        var head = cells(line);
        i += 2;
        var rows = [];
        while (i < lines.length && TABLE_ROW.test(lines[i])) { rows.push(cells(lines[i])); i++; }
        out.push('<div class="table-wrap"><table dir="auto"><thead><tr>' +
          head.map(function (h) { return "<th>" + inline(h) + "</th>"; }).join("") + "</tr></thead><tbody>" +
          rows.map(function (r) {
            return "<tr>" + r.map(function (c) { return "<td>" + inline(c) + "</td>"; }).join("") + "</tr>";
          }).join("") + "</tbody></table></div>");
        continue;
      }

      var h = line.match(HEADING);
      if (h) { flushPara(); out.push('<h' + (h[1].length + 2) + ' dir="auto">' + inline(h[2]) + "</h" + (h[1].length + 2) + ">"); i++; continue; }

      if (OL.test(line) || UL.test(line)) {
        flushPara();
        var ordered = OL.test(line);
        var start = ordered ? parseInt(line.match(OL)[1], 10) : 1;
        var items = [];
        while (i < lines.length && lines[i].trim() && (OL.test(lines[i]) || UL.test(lines[i]) || /^\s{2,}\S/.test(lines[i]))) {
          var m = lines[i].match(OL) || lines[i].match(UL);
          if (m) items.push(m[m.length - 1]);
          else if (items.length) items[items.length - 1] += " " + lines[i].trim();   // wrapped line
          i++;
        }
        var tag = ordered ? "ol" : "ul";
        out.push("<" + tag + (ordered && start !== 1 ? ' start="' + start + '"' : "") + ' dir="auto">' +
          items.map(function (it) { return "<li>" + inline(it) + "</li>"; }).join("") + "</" + tag + ">");
        continue;
      }

      para.push(line);
      i++;
    }
    flushPara();
    return out.join("");
  }

  window.Markdown = { render: render, escape: esc };
})();
