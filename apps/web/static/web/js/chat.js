/* Chat page: ask questions, render answers with sources/refusals/feedback, saved conversations.
   Conversation memory: every question is sent with its conversation_id; the backend loads the
   previous turns of that conversation and uses them to resolve follow-up questions. */
(function () {
  "use strict";
  var t = window.I18N.t;

  var SUGGESTIONS = {
    ar: [
      "كم مادة أقدر أسجل بأول فصل؟",
      "رسبت بمادة، هل بتأثر تسجيلي للمادة اللي بعدها؟",
      "شو بقي لي عشان أتخرج؟",
      "شو المتطلب السابق لمادة هندسة البرمجيات بخضوري؟",
      "كم ساعة لازم أخلص عشان أتخرج من القانون بجامعة النجاح؟",
      "هل بقدر أنسحب من مادة؟ ولحد إمتى؟"
    ],
    en: [
      "How many courses can I register in my first semester?",
      "I failed a course — does it affect registering for the next one?",
      "What do I still need to graduate?",
      "What is the prerequisite of Software Engineering at Kadoorie?",
      "How many credit hours do I need to graduate in Law at An-Najah?",
      "Can I withdraw from a course, and until when?"
    ]
  };

  var els = {};
  var state = { conversationId: null, busy: false, conversations: [] };

  // ---------- helpers ----------
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function scrollDown() {
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function avatar() {
    var wrap = el("div", "avatar");
    wrap.appendChild(document.getElementById("cat-avatar").content.cloneNode(true));
    return wrap;
  }

  function hideWelcome() { els.welcome.hidden = true; }

  function clearMessages() {
    Array.from(els.messages.children).forEach(function (c) { if (c !== els.welcome) c.remove(); });
  }

  // ---------- rendering ----------
  function renderSuggestions() {
    els.suggestions.innerHTML = "";
    SUGGESTIONS[window.I18N.lang()].forEach(function (q) {
      var chip = el("button", "chip", q);
      chip.type = "button";
      chip.dir = "auto";
      chip.addEventListener("click", function () { ask(q); });
      els.suggestions.appendChild(chip);
    });
  }

  function addUserMessage(text) {
    var row = el("div", "msg msg-user");
    var bubble = el("div", "bubble", text);
    bubble.dir = "auto";
    row.appendChild(bubble);
    els.messages.appendChild(row);
    scrollDown();
    return row;
  }

  function sourceLocation(s) {
    var parts = [];
    if (s.page) parts.push(t("page") + " " + s.page);
    if (s.article) parts.push(s.article);
    return parts.join(" · ");
  }

  function renderSources(sources) {
    var box = el("div", "sources");
    box.appendChild(el("div", "sources-title", t("sources")));
    sources.forEach(function (s, i) {
      var card = el("details", "source-card");
      var summary = el("summary");
      summary.appendChild(el("span", "source-num", "[" + (i + 1) + "]"));
      var doc = el("span", "source-doc", s.title || s.document);
      doc.dir = "auto";
      summary.appendChild(doc);
      var meta = el("span", "source-meta", sourceLocation(s));
      meta.dir = "auto";
      summary.appendChild(meta);
      var toggle = el("span", "source-toggle", t("showText"));
      summary.appendChild(toggle);
      card.appendChild(summary);
      var snippet = el("p", "source-snippet", s.snippet ? s.snippet + "…" : "");
      snippet.dir = "auto";
      card.appendChild(snippet);
      card.addEventListener("toggle", function () { toggle.textContent = card.open ? t("hideText") : t("showText"); });
      box.appendChild(card);
    });
    return box;
  }

  function renderFeedback(msg) {
    var footer = el("div", "msg-footer");
    var label = el("span", "", t("wasHelpful"));
    footer.appendChild(label);
    [["up", "👍", "helpful"], ["down", "👎", "notHelpful"]].forEach(function (f) {
      var btn = el("button", "fb-btn" + (msg.feedback === f[0] ? " selected" : ""), f[1]);
      btn.type = "button";
      btn.title = t(f[2]);
      btn.setAttribute("aria-label", t(f[2]));
      btn.setAttribute("aria-pressed", msg.feedback === f[0] ? "true" : "false");
      btn.addEventListener("click", async function () {
        var rating = msg.feedback === f[0] ? null : f[0];      // click again to clear
        var res = await window.API.post("/messages/" + msg.id + "/feedback/", { rating: rating });
        if (!res.ok) return;
        msg.feedback = res.data.feedback;
        footer.querySelectorAll(".fb-btn").forEach(function (b) {
          b.classList.remove("selected");
          b.setAttribute("aria-pressed", "false");
        });
        if (msg.feedback) {
          btn.classList.add("selected");
          btn.setAttribute("aria-pressed", "true");
          label.textContent = t("thanks");
        } else {
          label.textContent = t("wasHelpful");
        }
      });
      footer.appendChild(btn);
    });
    return footer;
  }

  function addBotMessage(msg) {
    var refused = msg.refused;
    var row = el("div", "msg msg-bot" + (refused ? " refusal" : ""));
    row.appendChild(avatar());
    var bubble = el("div", "bubble");

    if (refused) {
      var title = msg.reason === "out_of_scope" ? t("refusalOutOfScopeTitle") : t("refusalNotFoundTitle");
      bubble.appendChild(el("div", "refusal-title", "⚠️ " + title));
      var body = el("div");
      body.innerHTML = window.Markdown.render(msg.content);
      bubble.appendChild(body);
      if (msg.reason !== "out_of_scope") bubble.appendChild(el("div", "refusal-hint", t("refusalHint")));
    } else {
      var content = el("div");
      content.innerHTML = window.Markdown.render(msg.content);
      bubble.appendChild(content);
      if (msg.sources && msg.sources.length) bubble.appendChild(renderSources(msg.sources));
    }
    if (msg.id && msg.reason !== "greeting") bubble.appendChild(renderFeedback(msg));

    row.appendChild(bubble);
    els.messages.appendChild(row);
    scrollDown();
    return row;
  }

  function addTyping() {
    var row = el("div", "msg msg-bot");
    row.appendChild(avatar());
    var bubble = el("div", "bubble");
    var dots = el("span", "typing");
    dots.innerHTML = "<span></span><span></span><span></span>";
    bubble.appendChild(dots);
    bubble.appendChild(el("span", "typing-label", t("thinking")));
    row.appendChild(bubble);
    els.messages.appendChild(row);
    scrollDown();
    return row;
  }

  function addError(message, retryQuestion) {
    var row = el("div", "msg msg-bot error");
    row.appendChild(avatar());
    var bubble = el("div", "bubble");
    bubble.appendChild(el("div", "", message));
    if (retryQuestion) {
      var btn = el("button", "btn btn-ghost", t("retry"));
      btn.type = "button";
      btn.addEventListener("click", function () { row.remove(); ask(retryQuestion, { skipUserBubble: true }); });
      bubble.appendChild(btn);
    }
    row.appendChild(bubble);
    els.messages.appendChild(row);
    scrollDown();
  }

  // ---------- asking ----------
  function setBusy(busy) {
    state.busy = busy;
    els.send.disabled = busy;
    els.question.disabled = busy;
  }

  async function ask(question, opts) {
    opts = opts || {};
    question = (question || "").trim();
    if (!question || state.busy) return;
    hideWelcome();
    if (!opts.skipUserBubble) addUserMessage(question);
    els.question.value = "";
    autoresize();
    setBusy(true);
    var typing = addTyping();

    var res = await window.API.post("/chat/ask/", {
      question: question, conversation_id: state.conversationId
    }, { timeout: 120000 });

    typing.remove();
    setBusy(false);
    els.question.focus();

    if (!res.ok) {
      if (res.error.code === "unauthorized") { window.location.href = "/login/?next=/"; return; }
      if (res.error.code === "llm_unavailable" || res.error.code === "network") els.question.value = question;
      addError(window.API.friendlyError(res), question);
      return;
    }
    var isNew = state.conversationId !== res.data.conversation.id;
    state.conversationId = res.data.conversation.id;
    addBotMessage(res.data.answer);
    if (isNew) await loadConversations(); else markActive();
  }

  // ---------- conversations ----------
  function markActive() {
    els.convList.querySelectorAll(".conv-item").forEach(function (li) {
      li.classList.toggle("active", Number(li.dataset.id) === state.conversationId);
    });
  }

  async function loadConversations() {
    var res = await window.API.get("/conversations/");
    if (!res.ok) return;
    state.conversations = res.data.results;
    els.convList.innerHTML = "";
    els.convEmpty.hidden = state.conversations.length > 0;
    state.conversations.forEach(function (c) {
      var li = el("li", "conv-item");
      li.dataset.id = c.id;
      var open = el("button", "conv-open", c.title);
      open.type = "button";
      open.dir = "auto";
      open.title = c.title;
      open.addEventListener("click", function () { openConversation(c.id); });
      li.appendChild(open);

      var actions = el("span", "conv-actions");
      var rename = el("button", "icon-btn", "✎");
      rename.type = "button";
      rename.title = t("rename");
      rename.setAttribute("aria-label", t("rename"));
      rename.addEventListener("click", async function () {
        var title = window.prompt(t("renamePrompt"), c.title);
        if (!title || !title.trim()) return;
        var r = await window.API.patch("/conversations/" + c.id + "/", { title: title.trim() });
        if (r.ok) loadConversations();
      });
      var remove = el("button", "icon-btn", "🗑");
      remove.type = "button";
      remove.title = t("remove");
      remove.setAttribute("aria-label", t("remove"));
      remove.addEventListener("click", async function () {
        if (!window.confirm(t("confirmDelete"))) return;
        var r = await window.API.del("/conversations/" + c.id + "/");
        if (!r.ok) return;
        if (state.conversationId === c.id) newChat();
        loadConversations();
      });
      actions.appendChild(rename);
      actions.appendChild(remove);
      li.appendChild(actions);
      els.convList.appendChild(li);
    });
    markActive();
  }

  async function openConversation(id) {
    if (state.busy) return;
    var res = await window.API.get("/conversations/" + id + "/");
    if (!res.ok) { addError(window.API.friendlyError(res)); return; }
    state.conversationId = id;
    clearMessages();
    hideWelcome();
    res.data.messages.forEach(function (m) {
      if (m.role === "user") addUserMessage(m.content); else addBotMessage(m);
    });
    markActive();
    closeSidebar();
  }

  function newChat() {
    state.conversationId = null;
    clearMessages();
    els.welcome.hidden = false;
    markActive();
    closeSidebar();
    els.question.focus();
  }

  // ---------- layout ----------
  function autoresize() {
    els.question.style.height = "auto";
    els.question.style.height = Math.min(els.question.scrollHeight, 160) + "px";
  }

  function closeSidebar() { document.body.classList.remove("sidebar-open"); }

  document.addEventListener("DOMContentLoaded", function () {
    els = {
      messages: document.getElementById("messages"),
      welcome: document.getElementById("welcome"),
      suggestions: document.getElementById("suggestions"),
      composer: document.getElementById("composer"),
      question: document.getElementById("question"),
      send: document.getElementById("send"),
      convList: document.getElementById("conv-list"),
      convEmpty: document.getElementById("conv-empty")
    };

    renderSuggestions();
    loadConversations();

    els.composer.addEventListener("submit", function (e) { e.preventDefault(); ask(els.question.value); });
    els.question.addEventListener("input", autoresize);
    els.question.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); ask(els.question.value); }
    });
    document.getElementById("new-chat").addEventListener("click", newChat);

    var toggle = document.getElementById("sidebar-toggle");
    if (toggle) toggle.addEventListener("click", function () { document.body.classList.toggle("sidebar-open"); });
    document.getElementById("sidebar-backdrop").addEventListener("click", closeSidebar);

    document.addEventListener("langchange", renderSuggestions);
    els.question.focus();
  });
})();
