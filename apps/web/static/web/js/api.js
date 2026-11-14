/* Thin fetch wrapper for /api/v1: session cookie + CSRF header, uniform result, friendly errors. */
(function () {
  "use strict";
  var BASE = "/api/v1";

  function cookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  /** Returns {ok, status, data, error:{code,message}} — never throws. */
  async function request(method, path, body, opts) {
    opts = opts || {};
    var headers = { "Accept": "application/json", "X-CSRFToken": cookie("csrftoken") };
    var payload;
    if (body instanceof FormData) {
      payload = body;                                  // browser sets the multipart boundary
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json; charset=utf-8";
      payload = JSON.stringify(body);
    }
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, opts.timeout || 90000);
    try {
      var res = await fetch(BASE + path, {
        method: method, headers: headers, body: payload, credentials: "same-origin", signal: controller.signal
      });
      var data = res.status === 204 ? null : await res.json().catch(function () { return null; });
      if (res.ok) return { ok: true, status: res.status, data: data };
      var err = (data && data.error) || { code: "server_error", message: "" };
      if (res.status === 401 || (res.status === 403 && err.code === "unauthorized")) {
        err.code = "unauthorized";
      }
      return { ok: false, status: res.status, data: data, error: err };
    } catch (e) {
      return { ok: false, status: 0, data: null, error: { code: "network", message: String(e) } };
    } finally {
      clearTimeout(timer);
    }
  }

  /** A user-facing message for an API error, in the current UI language. */
  function friendlyError(result) {
    var t = window.I18N.t;
    var code = result.error && result.error.code;
    if (code === "network") return t("errNetwork");
    if (code === "rate_limited") return t("errRateLimit");
    if (code === "llm_unavailable") return t("errLLM");
    if (code === "unauthorized") return t("errAuth");
    if (code === "validation_error" || code === "not_found" || code === "forbidden" ||
        code === "file_too_large" || code === "unsupported_file_type" || code === "conflict") {
      return result.error.message || t("errServer");
    }
    return t("errServer");
  }

  /** GET every page of a paginated list endpoint; returns {ok, data: {results: [...]}} like get(). */
  async function getAll(path, opts) {
    var results = [];
    var next = path;
    while (next) {
      var res = await request("GET", next, undefined, opts);
      if (!res.ok) return res;
      results = results.concat(res.data.results);
      // "next" is an absolute URL; keep only the part after /api/v1 so request() can reuse it.
      next = res.data.next ? res.data.next.slice(res.data.next.indexOf(BASE) + BASE.length) : null;
    }
    return { ok: true, status: 200, data: { results: results } };
  }

  window.API = {
    get: function (p, o) { return request("GET", p, undefined, o); },
    getAll: getAll,
    post: function (p, b, o) { return request("POST", p, b === undefined ? {} : b, o); },
    patch: function (p, b, o) { return request("PATCH", p, b, o); },
    del: function (p, o) { return request("DELETE", p, undefined, o); },
    friendlyError: friendlyError
  };
})();
