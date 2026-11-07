/* UI strings (Arabic default, English toggle) and RTL/LTR switching.
   Elements use data-i18n="key" (text), data-i18n-placeholder, data-i18n-aria,
   or data-ar / data-en for values that come from the server (e.g. the product name). */
(function () {
  "use strict";

  var STRINGS = {
    ar: {
      navChat: "المحادثة", navDocuments: "المستندات", navAnalytics: "الإحصائيات", navAdmin: "لوحة الإدارة",
      logout: "خروج", langButton: "English",
      footer: "للقرارات المهمة (التسجيل، الانسحاب، التخرج) تأكّد دائمًا من دائرة القبول والتسجيل.",
      loginIntro: "قطّ الحرم الجامعي: موجود هون من زمان، وبعرف كل الأنظمة… وبعطيك المصدر دايمًا.",
      loginError: "اسم المستخدم أو كلمة المرور غير صحيحة.", username: "اسم المستخدم", password: "كلمة المرور",
      login: "دخول", demoAccounts: "حسابات تجريبية:",
      newChat: "+ محادثة جديدة", conversations: "محادثاتي", noConversations: "لا توجد محادثات بعد.",
      welcomeTitle: "أهلًا! أنا قطّ الحرم 🐾",
      welcomeText: "صرلي هون أكتر من أي حدا، وبعرف كل الأنظمة والخطط الدراسية. اسألني بلهجتك، وبجاوبك من مستندات الجامعة الرسمية مع المصدر.",
      suggestTitle: "جرّب تسأل:", placeholder: "اكتب سؤالك هنا…", send: "إرسال",
      thinking: "القطّ بدوّر بالمستندات…", sources: "المصادر", page: "صفحة", showText: "عرض النص", hideText: "إخفاء النص",
      refusalNotFoundTitle: "المعلومة غير موجودة في المستندات المتاحة",
      refusalOutOfScopeTitle: "خارج نطاق عملي",
      refusalHint: "📍 للتأكد، راجع دائرة القبول والتسجيل في جامعتك.",
      helpful: "مفيد", notHelpful: "غير مفيد", wasHelpful: "هل كانت الإجابة مفيدة؟", thanks: "شكرًا لملاحظتك!",
      rename: "إعادة تسمية", remove: "حذف", renamePrompt: "العنوان الجديد للمحادثة:",
      confirmDelete: "حذف هذه المحادثة نهائيًا؟", retry: "إعادة المحاولة",
      errNetwork: "تعذّر الاتصال بالخادم. تأكّد من الإنترنت وحاول مرة أخرى.",
      errRateLimit: "أرسلت أسئلة كثيرة بسرعة. استنّى دقيقة وجرّب مرة ثانية.",
      errLLM: "خدمة الذكاء الاصطناعي مشغولة حاليًا أو انتهت الحصة المجانية مؤقتًا. حاول بعد قليل.",
      errAuth: "انتهت الجلسة. سجّل الدخول من جديد.", errServer: "صار خطأ غير متوقع. حاول مرة ثانية.",
      // staff
      docsTitle: "مستندات الجامعة", uploadTitle: "رفع مستند جديد", file: "الملف (PDF أو TXT، حتى 20MB)",
      docTitle: "العنوان (اختياري)", year: "سنة الإصدار", upload: "رفع وفهرسة", reindex: "إعادة فهرسة الكل",
      reindexConfirm: "إعادة بناء الفهرس بالكامل تستغرق حوالي 5 دقائق. متابعة؟", reindexing: "جارٍ إعادة الفهرسة…",
      indexStatus: "حالة الفهرس", chunks: "مقطع", documentsCount: "مستند", colTitle: "العنوان", colFile: "الملف",
      colYear: "السنة", colStatus: "الحالة", colChunks: "المقاطع", colUploaded: "تاريخ الرفع", colActions: "",
      ready: "جاهز", processing: "قيد المعالجة", failed: "فشل", noDocs: "لا توجد مستندات.",
      uploaded: "تم رفع الملف، وتجري فهرسته الآن.", confirmDocDelete: "حذف هذا المستند من الفهرس؟",
      // analytics
      analyticsTitle: "لوحة الإحصائيات", period: "الفترة", days7: "آخر 7 أيام", days30: "آخر 30 يومًا", days90: "آخر 90 يومًا",
      totalQuestions: "عدد الأسئلة", activeUsers: "المستخدمون النشطون", refusalRate: "نسبة الرفض",
      avgLatency: "متوسط زمن الإجابة", feedbackLabel: "تقييم الإجابات", perDay: "الأسئلة يوميًا",
      topQuestions: "الأسئلة الأكثر تكرارًا", colQuestion: "السؤال", colCount: "التكرار", colRefused: "مرفوض",
      noData: "لا توجد بيانات بعد.", seconds: "ث",
      refusedHint: "الأسئلة المرفوضة كثيرًا تعني أن المعلومة ناقصة في المستندات."
    },
    en: {
      navChat: "Chat", navDocuments: "Documents", navAnalytics: "Analytics", navAdmin: "Admin",
      logout: "Log out", langButton: "العربية",
      footer: "For important decisions (registration, withdrawal, graduation), always confirm with the Admissions & Registration office.",
      loginIntro: "The campus cat: been here longer than anyone, knows every rule… and always shows the source.",
      loginError: "Wrong username or password.", username: "Username", password: "Password",
      login: "Log in", demoAccounts: "Demo accounts:",
      newChat: "+ New chat", conversations: "My chats", noConversations: "No chats yet.",
      welcomeTitle: "Hi! I'm the campus cat 🐾",
      welcomeText: "I've been on campus longer than anyone and I know every rule and study plan. Ask me anything — I answer only from official university documents, with the source.",
      suggestTitle: "Try asking:", placeholder: "Type your question…", send: "Send",
      thinking: "The cat is searching the documents…", sources: "Sources", page: "page", showText: "Show text", hideText: "Hide text",
      refusalNotFoundTitle: "Not found in the available documents",
      refusalOutOfScopeTitle: "Outside what I can help with",
      refusalHint: "📍 Please check with your university's Admissions & Registration office.",
      helpful: "Helpful", notHelpful: "Not helpful", wasHelpful: "Was this helpful?", thanks: "Thanks for the feedback!",
      rename: "Rename", remove: "Delete", renamePrompt: "New chat title:",
      confirmDelete: "Delete this chat permanently?", retry: "Try again",
      errNetwork: "Can't reach the server. Check your connection and try again.",
      errRateLimit: "Too many questions too fast. Please wait a minute and try again.",
      errLLM: "The AI service is busy or the free quota is temporarily used up. Please try again shortly.",
      errAuth: "Your session expired. Please log in again.", errServer: "Something went wrong. Please try again.",
      docsTitle: "University documents", uploadTitle: "Upload a new document", file: "File (PDF or TXT, up to 20 MB)",
      docTitle: "Title (optional)", year: "Year", upload: "Upload & index", reindex: "Re-index all",
      reindexConfirm: "Rebuilding the whole index takes about 5 minutes. Continue?", reindexing: "Re-indexing…",
      indexStatus: "Index status", chunks: "chunks", documentsCount: "documents", colTitle: "Title", colFile: "File",
      colYear: "Year", colStatus: "Status", colChunks: "Chunks", colUploaded: "Uploaded", colActions: "",
      ready: "Ready", processing: "Processing", failed: "Failed", noDocs: "No documents.",
      uploaded: "File uploaded and is being indexed.", confirmDocDelete: "Remove this document from the index?",
      analyticsTitle: "Analytics", period: "Period", days7: "Last 7 days", days30: "Last 30 days", days90: "Last 90 days",
      totalQuestions: "Questions", activeUsers: "Active users", refusalRate: "Refusal rate",
      avgLatency: "Avg. answer time", feedbackLabel: "Answer feedback", perDay: "Questions per day",
      topQuestions: "Most asked questions", colQuestion: "Question", colCount: "Count", colRefused: "Refused",
      noData: "No data yet.", seconds: "s",
      refusedHint: "Often-refused questions mean the documents are missing that information."
    }
  };

  function lang() {
    return document.documentElement.lang === "en" ? "en" : "ar";
  }

  function t(key) {
    return (STRINGS[lang()] && STRINGS[lang()][key]) || STRINGS.ar[key] || key;
  }

  function apply(root) {
    root = root || document;
    root.querySelectorAll("[data-i18n]").forEach(function (el) { el.textContent = t(el.dataset.i18n); });
    root.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) { el.placeholder = t(el.dataset.i18nPlaceholder); });
    root.querySelectorAll("[data-i18n-aria]").forEach(function (el) { el.setAttribute("aria-label", t(el.dataset.i18nAria)); });
    root.querySelectorAll("[data-ar]").forEach(function (el) { el.textContent = el.dataset[lang()] || el.dataset.ar; });
    var btn = document.getElementById("lang-toggle");
    if (btn) btn.textContent = t("langButton");
    document.title = (document.querySelector(".brand-name") || {}).textContent || document.title;
  }

  function setLang(value) {
    document.documentElement.lang = value;
    document.documentElement.dir = value === "ar" ? "rtl" : "ltr";
    try { localStorage.setItem("lang", value); } catch (e) {}
    apply();
    document.dispatchEvent(new CustomEvent("langchange", { detail: value }));
  }

  document.addEventListener("DOMContentLoaded", function () {
    apply();
    var btn = document.getElementById("lang-toggle");
    if (btn) btn.addEventListener("click", function () { setLang(lang() === "ar" ? "en" : "ar"); });
  });

  window.I18N = { t: t, lang: lang, apply: apply, setLang: setLang };
})();
