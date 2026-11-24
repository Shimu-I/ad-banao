/* AdBanao admin console. No build step. Talks to /admin/* on the API with the sign-in cookie.
 * All user-supplied text is inserted with textContent, never as HTML. */
(function () {
  "use strict";
  var API = (window.ADBANAO_API || "http://" + ((window.location.hostname && /^[\w.\-]+$/.test(window.location.hostname)) ? window.location.hostname : "localhost") + ":8000").replace(/\/$/, "");
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- copy ---------- */
  var T = {
    en: {
      title: "Admin Dashboard", subtitle: "Overview of your AdBanao platform", soon: "Soon",
      "nav.dashboard": "Dashboard", "nav.users": "Users", "nav.activity": "Activity Log", "nav.analytics": "Analytics", "nav.settings": "Settings",
      "side.t": "Helping Bangladeshi Businesses Grow", "side.s": "Smarter ads. Greater reach.",
      "menu.home": "Back to home page", "menu.signout": "Sign out",
      "denied.t": "Admins only", "denied.d": "This page is for AdBanao administrators. Your account does not have admin access.",
      "err.t": "Could not load the dashboard", retry: "Try again",
      "p.today": "Today", "p.7d": "7 days", "p.30d": "30 days", "p.custom": "Custom", from: "From", to: "To", apply: "Apply",
      "dl.users": "Download users (CSV)", "dl.activity": "Download activity (CSV)",
      search: "Search users…", "f.allStatus": "All statuses", "f.allRoles": "All roles", "f.allLang": "All languages",
      "s.active": "Active", "s.suspended": "Suspended", "r.user": "User", "r.admin": "Admin",
      "g.all": "All events", "g.signin": "Sign-ins", "g.content": "Brands and products", "g.account": "Account changes", "g.admin": "Admin actions",
      "a.period": "Selected period", "a.all": "All time",
      "p.recent": "Recent activity", "p.viewall": "View all activity", cancel: "Cancel",
      total: "Total users", signups: "New sign-ups", active: "Active users", signins: "Sign-ins", ads: "Ads created",
      vs: "vs previous period", noCompare: "no earlier data", comingSoon: "coming soon",
      "c.signups": "Sign-ups per day", "c.active": "Active users per day", "c.top": "Top users",
      chart: "Chart", table: "Table", date: "Date", count: "Count",
      topLine: "{s} sign-ins • {a} actions", noTop: "No activity in this period.", noData: "Nothing to show yet.",
      range: "Showing {a} to {b} (UTC days).",
      "h.name": "Name", "h.email": "Email", "h.business": "Business", "h.lang": "Language", "h.joined": "Joined", "h.last": "Last active", "h.signins": "Sign-ins", "h.brands": "Brands", "h.products": "Products", "h.status": "Status",
      never: "Never", justNow: "just now", mAgo: "{n}m ago", hAgo: "{n}h ago", dAgo: "{n}d ago",
      of: "{a}–{b} of {t}", none: "No users match.", noEvents: "No activity yet.", demo: "Demo", you: "You",
      "p.phone": "Phone", "p.business": "Business", "p.language": "Language", "p.joined": "Joined", "p.last": "Last active", "p.sessions": "Signed-in browsers",
      "act.suspend": "Suspend account", "act.reactivate": "Reactivate account", "act.makeAdmin": "Make admin", "act.removeAdmin": "Remove admin", "act.signout": "Sign out everywhere",
      selfNote: "You cannot suspend or demote yourself. Ask another admin.",
      "c.suspend.t": "Suspend this account?", "c.suspend.b": "{n} will be signed out now and cannot sign in until you reactivate the account. Their data is kept.",
      "c.react.t": "Reactivate this account?", "c.react.b": "{n} will be able to sign in again.",
      "c.make.t": "Make this person an admin?", "c.make.b": "{n} will see this admin page and can suspend and promote other users. They also need a secret word, set on the server with: make admin EMAIL=their email.",
      "c.remove.t": "Remove admin access?", "c.remove.b": "{n} will no longer see this admin page.",
      "c.out.t": "Sign out everywhere?", "c.out.b": "{n} will be signed out of every browser. They can sign in again.",
      "t.suspend": "Account suspended.", "t.react": "Account reactivated.", "t.make": "Admin access given.", "t.remove": "Admin access removed.", "t.out": "Signed out everywhere.", "t.dl": "Download started.", "t.fail": "Something went wrong.",
      "e.signup": "Created an account", "e.login": "Signed in", "e.login_failed": "Signed in (wrong password)", "e.login_blocked": "Tried to sign in (account suspended)", "e.logout": "Signed out",
      "e.password_changed": "Changed password", "e.profile_updated": "Updated profile", "e.brand_created": "Created brand", "e.brand_updated": "Updated brand", "e.brand_archived": "Archived brand", "e.brand_restored": "Restored brand",
      "e.product_created": "Created product", "e.product_updated": "Updated product", "e.product_archived": "Archived product", "e.product_restored": "Restored product",
      "e.admin_role_changed": "Role changed", "e.admin_suspended": "Account suspended", "e.admin_reactivated": "Account reactivated", "e.admin_signed_out_user": "Signed out everywhere", "e.admin_login": "Admin sign-in", "e.admin_login_failed": "Admin sign-in failed",
      "p.secret": "Secret word", "yes": "Set", "no": "Not set", by: "by {n}", unknownUser: "Unknown visitor", offline: "Cannot reach the server. Check your connection and try again.", viewing: "Showing: {n}", clear: "Clear"
    },
    bn: {
      title: "অ্যাডমিন ড্যাশবোর্ড", subtitle: "আপনার অ্যাডবানাও প্ল্যাটফর্মের সারসংক্ষেপ", soon: "শীঘ্রই",
      "nav.dashboard": "ড্যাশবোর্ড", "nav.users": "ব্যবহারকারী", "nav.activity": "কার্যকলাপের লগ", "nav.analytics": "অ্যানালিটিক্স", "nav.settings": "সেটিংস",
      "side.t": "বাংলাদেশি ব্যবসার প্রসারে পাশে আছি", "side.s": "স্মার্ট বিজ্ঞাপন। বড় নাগাল।",
      "menu.home": "হোম পেজে ফিরুন", "menu.signout": "সাইন আউট",
      "denied.t": "শুধু অ্যাডমিনদের জন্য", "denied.d": "এই পেজ অ্যাডবানাও অ্যাডমিনদের জন্য। আপনার অ্যাকাউন্টে অ্যাডমিন অনুমতি নেই।",
      "err.t": "ড্যাশবোর্ড লোড করা যায়নি", retry: "আবার চেষ্টা করুন",
      "p.today": "আজ", "p.7d": "৭ দিন", "p.30d": "৩০ দিন", "p.custom": "কাস্টম", from: "শুরু", to: "শেষ", apply: "প্রয়োগ",
      "dl.users": "ব্যবহারকারী ডাউনলোড (CSV)", "dl.activity": "কার্যকলাপ ডাউনলোড (CSV)",
      search: "ব্যবহারকারী খুঁজুন…", "f.allStatus": "সব অবস্থা", "f.allRoles": "সব ভূমিকা", "f.allLang": "সব ভাষা",
      "s.active": "সক্রিয়", "s.suspended": "স্থগিত", "r.user": "ব্যবহারকারী", "r.admin": "অ্যাডমিন",
      "g.all": "সব ঘটনা", "g.signin": "সাইন-ইন", "g.content": "ব্র্যান্ড ও পণ্য", "g.account": "অ্যাকাউন্ট পরিবর্তন", "g.admin": "অ্যাডমিনের কাজ",
      "a.period": "নির্বাচিত সময়", "a.all": "সব সময়",
      "p.recent": "সাম্প্রতিক কার্যকলাপ", "p.viewall": "সব কার্যকলাপ দেখুন", cancel: "বাতিল",
      total: "মোট ব্যবহারকারী", signups: "নতুন সাইন-আপ", active: "সক্রিয় ব্যবহারকারী", signins: "সাইন-ইন", ads: "তৈরি বিজ্ঞাপন",
      vs: "আগের সময়ের তুলনায়", noCompare: "আগের তথ্য নেই", comingSoon: "শীঘ্রই আসছে",
      "c.signups": "প্রতিদিনের সাইন-আপ", "c.active": "প্রতিদিনের সক্রিয় ব্যবহারকারী", "c.top": "শীর্ষ ব্যবহারকারী",
      chart: "চার্ট", table: "টেবিল", date: "তারিখ", count: "সংখ্যা",
      topLine: "{s} সাইন-ইন • {a} কাজ", noTop: "এই সময়ে কোনো কার্যকলাপ নেই।", noData: "এখনও দেখানোর কিছু নেই।",
      range: "{a} থেকে {b} পর্যন্ত (UTC দিন)।",
      "h.name": "নাম", "h.email": "ইমেইল", "h.business": "ব্যবসা", "h.lang": "ভাষা", "h.joined": "যোগ দিয়েছেন", "h.last": "শেষ সক্রিয়", "h.signins": "সাইন-ইন", "h.brands": "ব্র্যান্ড", "h.products": "পণ্য", "h.status": "অবস্থা",
      never: "কখনো না", justNow: "এইমাত্র", mAgo: "{n} মিনিট আগে", hAgo: "{n} ঘণ্টা আগে", dAgo: "{n} দিন আগে",
      of: "{t}টির মধ্যে {a}–{b}", none: "কোনো ব্যবহারকারী মেলেনি।", noEvents: "এখনও কোনো কার্যকলাপ নেই।", demo: "ডেমো", you: "আপনি",
      "p.phone": "ফোন", "p.business": "ব্যবসা", "p.language": "ভাষা", "p.joined": "যোগ দিয়েছেন", "p.last": "শেষ সক্রিয়", "p.sessions": "সাইন-ইন করা ব্রাউজার",
      "act.suspend": "অ্যাকাউন্ট স্থগিত করুন", "act.reactivate": "অ্যাকাউন্ট চালু করুন", "act.makeAdmin": "অ্যাডমিন বানান", "act.removeAdmin": "অ্যাডমিন সরান", "act.signout": "সব জায়গা থেকে সাইন আউট",
      selfNote: "নিজেকে স্থগিত বা অ্যাডমিন থেকে সরানো যায় না। অন্য অ্যাডমিনকে বলুন।",
      "c.suspend.t": "এই অ্যাকাউন্ট স্থগিত করবেন?", "c.suspend.b": "{n} এখনই সাইন আউট হবেন এবং আপনি চালু না করা পর্যন্ত সাইন-ইন করতে পারবেন না। তথ্য থেকে যাবে।",
      "c.react.t": "অ্যাকাউন্ট আবার চালু করবেন?", "c.react.b": "{n} আবার সাইন-ইন করতে পারবেন।",
      "c.make.t": "একে অ্যাডমিন বানাবেন?", "c.make.b": "{n} এই অ্যাডমিন পেজ দেখতে এবং অন্যদের স্থগিত বা অ্যাডমিন করতে পারবেন। তাঁর একটি সিক্রেট ওয়ার্ডও লাগবে, সার্ভারে এই কমান্ডে দিন: make admin EMAIL=তাঁর ইমেইল।",
      "c.remove.t": "অ্যাডমিন অনুমতি সরাবেন?", "c.remove.b": "{n} আর এই অ্যাডমিন পেজ দেখতে পারবেন না।",
      "c.out.t": "সব জায়গা থেকে সাইন আউট করবেন?", "c.out.b": "{n} সব ব্রাউজার থেকে সাইন আউট হবেন। তিনি আবার সাইন-ইন করতে পারবেন।",
      "t.suspend": "অ্যাকাউন্ট স্থগিত হয়েছে।", "t.react": "অ্যাকাউন্ট চালু হয়েছে।", "t.make": "অ্যাডমিন অনুমতি দেওয়া হয়েছে।", "t.remove": "অ্যাডমিন অনুমতি সরানো হয়েছে।", "t.out": "সব জায়গা থেকে সাইন আউট হয়েছে।", "t.dl": "ডাউনলোড শুরু হয়েছে।", "t.fail": "কিছু একটা ভুল হয়েছে।",
      "e.signup": "অ্যাকাউন্ট খুলেছেন", "e.login": "সাইন-ইন করেছেন", "e.login_failed": "সাইন-ইন (ভুল পাসওয়ার্ড)", "e.login_blocked": "সাইন-ইনের চেষ্টা (অ্যাকাউন্ট স্থগিত)", "e.logout": "সাইন আউট করেছেন",
      "e.password_changed": "পাসওয়ার্ড বদলেছেন", "e.profile_updated": "প্রোফাইল আপডেট করেছেন", "e.brand_created": "ব্র্যান্ড বানিয়েছেন", "e.brand_updated": "ব্র্যান্ড আপডেট করেছেন", "e.brand_archived": "ব্র্যান্ড আর্কাইভ করেছেন", "e.brand_restored": "ব্র্যান্ড ফিরিয়েছেন",
      "e.product_created": "পণ্য বানিয়েছেন", "e.product_updated": "পণ্য আপডেট করেছেন", "e.product_archived": "পণ্য আর্কাইভ করেছেন", "e.product_restored": "পণ্য ফিরিয়েছেন",
      "e.admin_role_changed": "ভূমিকা বদলানো হয়েছে", "e.admin_suspended": "অ্যাকাউন্ট স্থগিত", "e.admin_reactivated": "অ্যাকাউন্ট চালু", "e.admin_signed_out_user": "সব জায়গা থেকে সাইন আউট", "e.admin_login": "অ্যাডমিন সাইন-ইন", "e.admin_login_failed": "অ্যাডমিন সাইন-ইন ব্যর্থ",
      "p.secret": "সিক্রেট ওয়ার্ড", "yes": "দেওয়া আছে", "no": "দেওয়া নেই", by: "{n} করেছেন", unknownUser: "অজানা দর্শক", offline: "সার্ভারে পৌঁছানো যাচ্ছে না। সংযোগ দেখে আবার চেষ্টা করুন।", viewing: "দেখানো হচ্ছে: {n}", clear: "মুছুন"
    }
  };

  /* ---------- state ---------- */
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } }
  };
  var lang = document.documentElement.getAttribute("lang") === "bn" ? "bn" : "en";
  var S = {
    me: null, period: "7d", start: "", end: "", overview: null,
    users: { q: "", status: "all", role: "all", language: "all", sort: "joined", dir: "desc", page: 1, per: 25, data: null },
    act: { group: "all", scope: "period", page: 1, per: 25, userId: null, userName: "", data: null },
    chartMode: { signups: "chart", active: "chart" }, detail: null, lastFocus: null
  };

  function t(key, vars) {
    var s = (T[lang] && T[lang][key]) || T.en[key] || key;
    if (vars) Object.keys(vars).forEach(function (k) { s = s.split("{" + k + "}").join(vars[k]); });
    return s;
  }
  var locale = function () { return lang === "bn" ? "bn-BD" : "en-GB"; };
  var nf = function (n) { return new Intl.NumberFormat(locale()).format(n); };
  function fmtDay(iso, withYear) {
    var d = new Date(iso.length === 10 ? iso + "T00:00:00Z" : iso);
    return new Intl.DateTimeFormat(locale(), { day: "numeric", month: "short", year: withYear ? "numeric" : undefined, timeZone: "UTC" }).format(d);
  }
  function fmtDate(iso) { return new Intl.DateTimeFormat(locale(), { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso)); }
  function ago(iso) {
    if (!iso) return t("never");
    var s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 60) return t("justNow");
    if (s < 3600) return t("mAgo", { n: nf(Math.floor(s / 60)) });
    if (s < 86400) return t("hAgo", { n: nf(Math.floor(s / 3600)) });
    if (s < 86400 * 7) return t("dAgo", { n: nf(Math.floor(s / 86400)) });
    return fmtDate(iso);
  }

  /* ---------- tiny DOM helpers ---------- */
  function h(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    });
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) c.forEach(function (x) { add(el, x); });
    else el.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
  }
  var NS = "http://www.w3.org/2000/svg";
  function s(tag, attrs) {
    var el = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { el.setAttribute(k, attrs[k]); });
    for (var i = 2; i < arguments.length; i++) if (arguments[i]) el.appendChild(arguments[i]);
    return el;
  }
  function icon(id, cls) { var e = s("svg", { "class": "i " + (cls || ""), "aria-hidden": "true" }); e.appendChild(s("use", { href: "#" + id })); return e; }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); }
  function initial(name) { return (name || "?").trim().charAt(0).toUpperCase() || "?"; }
  function avatar(name, big) { return h("span", { "class": "av" + (big ? " big" : ""), "aria-hidden": "true", text: initial(name) }); }

  /* ---------- API ---------- */
  function api(method, path, body, raw) {
    var opts = { method: method, credentials: "include", headers: {} };
    if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
    return fetch(API + path, opts).then(function (res) {
      if (raw && res.ok) return res;
      if (res.status === 204) return null;
      return res.json().catch(function () { return null; }).then(function (data) {
        if (!res.ok) {
          var d = data && data.detail, msg = typeof d === "string" ? d : t("t.fail");
          var err = new Error(msg); err.status = res.status; throw err;
        }
        return data;
      });
    }, function () { var e = new Error(t("offline")); e.status = 0; throw e; });
  }
  function qs(o) {
    return Object.keys(o).filter(function (k) { return o[k] !== "" && o[k] != null && o[k] !== "all"; })
      .map(function (k) { return encodeURIComponent(k) + "=" + encodeURIComponent(o[k]); }).join("&");
  }
  function periodParams() { var p = { period: S.period }; if (S.period === "custom") { p.start = S.start; p.end = S.end; } return p; }

  /* ---------- toast, tooltip ---------- */
  var toastTimer;
  function toast(msg, bad) {
    var el = $("#toast"); el.textContent = msg; el.className = "toast" + (bad ? " bad" : ""); el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { el.hidden = true; }, 3500);
  }
  function tip(el, text) {
    var box = $("#tip");
    function show(ev) {
      box.textContent = text; box.hidden = false;
      var r = el.getBoundingClientRect(), x = ev && ev.clientX ? ev.clientX : r.left + r.width / 2;
      var w = box.offsetWidth; box.style.left = Math.max(8, Math.min(innerWidth - w - 8, x - w / 2)) + "px"; box.style.top = Math.max(8, r.top - box.offsetHeight - 8) + "px";
    }
    function hide() { box.hidden = true; }
    el.addEventListener("mousemove", show); el.addEventListener("mouseenter", show); el.addEventListener("mouseleave", hide);
    el.addEventListener("focus", show); el.addEventListener("blur", hide);
  }

  /* ---------- static text ---------- */
  function applyStatic() {
    document.documentElement.setAttribute("lang", lang);
    $$("[data-i]").forEach(function (el) { el.textContent = t(el.getAttribute("data-i")); });
    $$("[data-i-ph]").forEach(function (el) { el.setAttribute("placeholder", t(el.getAttribute("data-i-ph"))); });
    document.title = (lang === "bn" ? "অ্যাডবানাও অ্যাডমিন" : "AdBanao Admin");
    $("#langBtn").setAttribute("aria-label", lang === "bn" ? "ভাষা বদলান" : "Switch language");
  }
  function setTheme(next) {
    document.documentElement.setAttribute("data-theme", next); store.set("adbanao-theme", next);
    $("#themeBtn").setAttribute("aria-checked", next === "dark" ? "true" : "false");
  }

  /* ---------- stat cards ---------- */
  var STATS = [
    ["total_users", "total", "i-users"], ["new_signups", "signups", "i-plus"], ["active_users", "active", "i-check"],
    ["sign_ins", "signins", "i-in"], ["ads_created", "ads", "i-mega"]
  ];
  function renderStats() {
    var box = $("#stats"); clear(box); var o = S.overview; if (!o) return;
    STATS.forEach(function (d) {
      var st = o[d[0]], detail;
      if (d[0] === "ads_created" && st.value === 0 && st.previous === 0) {
        detail = [icon("i-clock"), t("comingSoon")];
      } else if (st.change_pct === null) {
        detail = [h("span", { "class": "chg flat", text: "–" }), h("span", { "class": "vs", text: t("noCompare") })];
      } else {
        var up = st.change_pct > 0, flat = st.change_pct === 0;
        detail = [h("span", { "class": "chg " + (flat ? "flat" : up ? "up" : "down") }, flat ? "=" : up ? "↑" : "↓", " ", nf(Math.abs(st.change_pct)) + "%"), h("span", { "class": "vs", text: t("vs") })];
      }
      box.appendChild(h("article", { "class": "card stat" },
        h("div", { "class": "ic" }, icon(d[2])), h("div", { "class": "n", text: nf(st.value) }), h("div", { "class": "l", text: t(d[1]) }), h("div", { "class": "d" }, detail)));
    });
    $("#rangeNote").textContent = t("range", { a: fmtDay(o.start, true), b: fmtDay(o.end, true) });
  }

  /* ---------- charts ---------- */
  function niceMax(m) { if (m <= 5) return 5; var p = Math.pow(10, Math.floor(Math.log10(m))), f = m / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; }
  function chartCard(box, key, titleKey, iconId, points, kind) {
    clear(box);
    var mode = S.chartMode[key];
    var head = h("div", { "class": "chart-h" }, h("h2", null, icon(iconId), t(titleKey)),
      h("div", { "class": "toggle", role: "group", "aria-label": t(titleKey) },
        h("button", { type: "button", "aria-pressed": String(mode === "chart"), text: t("chart"), onclick: function () { S.chartMode[key] = "chart"; renderCharts(); } }),
        h("button", { type: "button", "aria-pressed": String(mode === "table"), text: t("table"), onclick: function () { S.chartMode[key] = "table"; renderCharts(); } })));
    box.appendChild(head);
    if (!points.length) { box.appendChild(h("div", { "class": "empty", text: t("noData") })); return; }
    if (mode === "table") {
      var rows = points.map(function (p) { return h("tr", null, h("td", { text: fmtDay(p.date, true) }), h("td", { text: nf(p.count) })); });
      box.appendChild(h("div", { "class": "table-scroll" }, h("table", { "class": "mini-table" }, h("thead", null, h("tr", null, h("th", { text: t("date") }), h("th", { text: t("count") }))), h("tbody", null, rows))));
      return;
    }
    var W = Math.max(300, Math.round(box.clientWidth - 32)) || 520, H = 250, L = 34, R = 8, Tp = 10, B = 28, iw = W - L - R, ih = H - Tp - B;
    var max = niceMax(Math.max.apply(null, points.map(function (p) { return p.count; })));
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": t(titleKey) + ": " + points.map(function (p) { return fmtDay(p.date) + " " + p.count; }).join(", ") });
    var y = function (v) { return Tp + ih - (v / max) * ih; };
    var axis = s("g", { "class": "axis" });
    for (var i = 0; i <= 4; i++) {
      var v = (max / 4) * i, yy = y(v);
      axis.appendChild(s("line", { "class": i === 0 ? "baseline" : "gridline", x1: L, x2: W - R, y1: yy, y2: yy }));
      var lab = s("text", { x: L - 6, y: yy + 4, "text-anchor": "end" }); lab.textContent = nf(Math.round(v * 10) / 10); axis.appendChild(lab);
    }
    var n = points.length, step = iw / n, every = Math.ceil(n / Math.max(2, Math.floor(iw / 62)));
    points.forEach(function (p, idx) {
      if (idx % every === 0) { var xl = s("text", { x: L + step * idx + step / 2, y: H - 8, "text-anchor": "middle" }); xl.textContent = fmtDay(p.date); axis.appendChild(xl); }
    });
    svg.appendChild(axis);
    var marks = s("g");
    if (kind === "bar") {
      var bw = Math.min(46, step * 0.62);
      points.forEach(function (p, idx) {
        var cx = L + step * idx + step / 2, top = y(p.count), hgt = Tp + ih - top, g = s("g");
        var hit = s("rect", { "class": "hit", x: L + step * idx, y: Tp, width: step, height: ih, tabindex: "0" });
        g.appendChild(hit);
        if (p.count > 0) {
          var r = Math.min(4, bw / 2, hgt);
          g.appendChild(s("path", { "class": "mark", d: "M" + (cx - bw / 2) + " " + (Tp + ih) + "V" + (top + r) + "Q" + (cx - bw / 2) + " " + top + " " + (cx - bw / 2 + r) + " " + top + "H" + (cx + bw / 2 - r) + "Q" + (cx + bw / 2) + " " + top + " " + (cx + bw / 2) + " " + (top + r) + "V" + (Tp + ih) + "Z" }));
        }
        tip(hit, fmtDay(p.date, true) + ": " + nf(p.count)); marks.appendChild(g);
      });
    } else {
      var pts = points.map(function (p, idx) { return [L + step * idx + step / 2, y(p.count)]; });
      marks.appendChild(s("polyline", { "class": "line", points: pts.map(function (q) { return q[0] + "," + q[1]; }).join(" ") }));
      points.forEach(function (p, idx) {
        var hit = s("circle", { "class": "hit", cx: pts[idx][0], cy: pts[idx][1], r: 16, tabindex: "0" });
        marks.appendChild(hit); marks.appendChild(s("circle", { "class": "dot", cx: pts[idx][0], cy: pts[idx][1], r: 4.5 }));
        tip(hit, fmtDay(p.date, true) + ": " + nf(p.count));
      });
    }
    svg.appendChild(marks);
    box.appendChild(h("div", { "class": "svgbox" }, svg));
  }
  function renderCharts() {
    var o = S.overview; if (!o) return;
    chartCard($("#cSignups"), "signups", "c.signups", "i-bars", o.signups_per_day, "bar");
    chartCard($("#cActive"), "active", "c.active", "i-trend", o.active_per_day, "line");
    var box = $("#cTop"); clear(box);
    box.appendChild(h("h2", null, icon("i-trophy"), t("c.top")));
    if (!o.top_users.length) { box.appendChild(h("div", { "class": "empty", text: t("noTop") })); return; }
    box.appendChild(h("ol", null, o.top_users.map(function (u, i) {
      return h("li", null, h("span", { "class": "rk", text: nf(i + 1) }), avatar(u.user.display_name),
        h("div", null, h("b", { text: u.user.display_name }), h("small", { text: t("topLine", { s: nf(u.sign_ins), a: nf(u.actions) }) })),
        u.user.is_demo ? h("span", { "class": "badge demo", text: t("demo") }) : null);
    })));
  }

  /* ---------- users ---------- */
  var COLS = [["name", "h.name"], ["email", "h.email"], [null, "h.business"], [null, "h.lang"], ["joined", "h.joined"], ["last_active", "h.last"], ["sign_ins", "h.signins"], ["brands", "h.brands"], ["products", "h.products"], [null, "h.status"]];
  function statusEl(u) { return h("span", { "class": "status" + (u.is_active ? "" : " off"), text: t(u.is_active ? "s.active" : "s.suspended") }); }
  function langName(l) { return l === "bn" ? "বাংলা" : "English"; }
  function renderUsers() {
    var d = S.users.data, head = $("#usersHead"), body = $("#usersBody"), cards = $("#usersCards");
    clear(head); clear(body); clear(cards);
    COLS.forEach(function (c) {
      var th = h("th", { scope: "col" });
      if (c[0]) {
        var active = S.users.sort === c[0];
        th.setAttribute("aria-sort", active ? (S.users.dir === "asc" ? "ascending" : "descending") : "none");
        th.appendChild(h("button", { type: "button", onclick: function () {
          if (S.users.sort === c[0]) S.users.dir = S.users.dir === "asc" ? "desc" : "asc"; else { S.users.sort = c[0]; S.users.dir = c[0] === "name" || c[0] === "email" ? "asc" : "desc"; }
          S.users.page = 1; loadUsers();
        } }, t(c[1]), active ? (S.users.dir === "asc" ? " ↑" : " ↓") : ""));
      } else th.textContent = t(c[1]);
      head.appendChild(th);
    });
    if (!d) return;
    if (!d.items.length) {
      body.appendChild(h("tr", null, h("td", { colspan: COLS.length, "class": "empty", text: t("none") })));
      cards.appendChild(h("div", { "class": "empty", text: t("none") }));
    }
    d.items.forEach(function (u) {
      var open = function () { openPanel(u.id); };
      var nameCell = h("div", { "class": "cell-name" }, avatar(u.display_name), h("span", { text: u.display_name }),
        u.role === "admin" ? h("span", { "class": "badge admin", text: t("r.admin") }) : null, u.is_demo ? h("span", { "class": "badge demo", text: t("demo") }) : null);
      var tr = h("tr", { tabindex: "0", onclick: open, onkeydown: function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } } },
        h("td", null, nameCell), h("td", { text: u.email }), h("td", { text: u.business_name || "–" }), h("td", { text: langName(u.language) }),
        h("td", { text: fmtDate(u.created_at) }), h("td", { text: ago(u.last_active) }), h("td", { text: nf(u.sign_ins) }), h("td", { text: nf(u.brands) }), h("td", { text: nf(u.products) }), h("td", null, statusEl(u)));
      body.appendChild(tr);
      cards.appendChild(h("article", { "class": "ucard", tabindex: "0", onclick: open, onkeydown: function (e) { if (e.key === "Enter") open(); } },
        h("div", { "class": "row" }, h("div", { "class": "cell-name" }, avatar(u.display_name), h("b", { text: u.display_name })), statusEl(u)),
        h("small", { text: u.email }),
        h("div", { "class": "row" }, u.role === "admin" ? h("span", { "class": "badge admin", text: t("r.admin") }) : h("span", null), u.is_demo ? h("span", { "class": "badge demo", text: t("demo") }) : h("small", { text: t("h.last") + ": " + ago(u.last_active) })),
        h("div", { "class": "nums" }, h("div", null, h("b", { text: nf(u.sign_ins) }), h("span", { text: t("h.signins") })), h("div", null, h("b", { text: nf(u.brands) }), h("span", { text: t("h.brands") })), h("div", null, h("b", { text: nf(u.products) }), h("span", { text: t("h.products") })))));
    });
    renderPager($("#usersPager"), d, function (p) { S.users.page = p; loadUsers(); });
  }
  function renderPager(box, d, go) {
    clear(box); if (!d) return;
    var pages = Math.max(1, Math.ceil(d.total / d.per_page)), cur = d.page;
    var a = d.total ? (cur - 1) * d.per_page + 1 : 0, b = Math.min(d.total, cur * d.per_page);
    box.appendChild(h("span", { "class": "sum", text: t("of", { a: nf(a), b: nf(b), t: nf(d.total) }) }));
    var btn = function (label, p, dis, current, aria) { return h("button", { type: "button", disabled: dis, "aria-label": aria, "aria-current": current ? "page" : null, text: label, onclick: function () { go(p); } }); };
    box.appendChild(btn("‹", cur - 1, cur <= 1, false, "Previous"));
    var shown = [];
    for (var p = 1; p <= pages; p++) if (p === 1 || p === pages || Math.abs(p - cur) <= 1) shown.push(p);
    var last = 0;
    shown.forEach(function (p) { if (p - last > 1) box.appendChild(h("span", { text: "…" })); box.appendChild(btn(nf(p), p, false, p === cur, null)); last = p; });
    box.appendChild(btn("›", cur + 1, cur >= pages, false, "Next"));
  }
  function loadUsers() {
    var u = S.users;
    return api("GET", "/admin/users?" + qs({ q: u.q.trim(), status: u.status, role: u.role, language: u.language, sort: u.sort, direction: u.dir, page: u.page, per_page: u.per }))
      .then(function (d) { u.data = d; renderUsers(); }).catch(fail);
  }

  /* ---------- activity ---------- */
  var EV_ICON = { signup: ["i-plus", ""], login: ["i-in", ""], login_failed: ["i-warn", "bad"], login_blocked: ["i-ban", "bad"], logout: ["i-out", ""], password_changed: ["i-edit", "warn"], profile_updated: ["i-edit", "warn"],
    admin_login: ["i-shield", ""], admin_login_failed: ["i-warn", "bad"], admin_role_changed: ["i-shield", "warn"], admin_suspended: ["i-ban", "bad"], admin_reactivated: ["i-check", ""], admin_signed_out_user: ["i-out", "warn"] };
  function evIcon(type) { return EV_ICON[type] || (type.indexOf("archived") > 0 ? ["i-edit", "warn"] : ["i-bars", ""]); }
  function feedItems(list, withUser) {
    return list.map(function (e) {
      var ic = evIcon(e.event_type), who = e.user ? e.user.display_name : t("unknownUser");
      var what = t("e." + e.event_type) + (e.detail && e.event_type !== "login_failed" ? " — " + e.detail : "") + (e.actor ? " (" + t("by", { n: e.actor.display_name }) + ")" : "");
      return h("li", null, h("span", { "class": "ev " + ic[1] }, icon(ic[0])),
        h("div", null, withUser ? h("div", { "class": "who-l", text: who }) : null, h("div", { "class": "what", text: what })),
        h("time", { datetime: e.created_at, title: new Date(e.created_at).toLocaleString(locale()), text: ago(e.created_at) }));
    });
  }
  function renderActivity() {
    var d = S.act.data, feed = $("#feed"); clear(feed);
    if (d) {
      if (!d.items.length) feed.appendChild(h("li", { "class": "empty", text: t("noEvents") }));
      feedItems(d.items, true).forEach(function (li) { feed.appendChild(li); });
      renderPager($("#actPager"), d, function (p) { S.act.page = p; loadActivity(); });
    }
    var chip = $("#aUserChip"); clear(chip); chip.hidden = !S.act.userId;
    if (S.act.userId) chip.appendChild(h("span", { "class": "badge" }, t("viewing", { n: S.act.userName }), " ", h("button", { type: "button", "aria-label": t("clear"), style: "background:none;border:0;padding:0 2px", onclick: function () { S.act.userId = null; S.act.page = 1; loadActivity(); } }, "×")));
  }
  function activityQuery() {
    var a = S.act, q = { group: a.group, user_id: a.userId };
    if (a.scope === "all") q.period = "all"; else Object.assign(q, periodParams());
    return q;
  }
  function loadActivity() {
    var a = S.act, q = activityQuery(); q.page = a.page; q.per_page = a.per;
    return api("GET", "/admin/activity?" + qs(q)).then(function (d) { a.data = d; renderActivity(); }).catch(fail);
  }

  /* ---------- user panel ---------- */
  function confirmDialog(title, body, yesLabel, danger) {
    return new Promise(function (resolve) {
      var dlg = $("#confirm"); $("#cTitle").textContent = title; $("#cBody").textContent = body;
      var yes = $("#cYes"); yes.textContent = yesLabel; yes.className = "btn " + (danger ? "danger" : "primary");
      dlg.addEventListener("close", function once() { dlg.removeEventListener("close", once); resolve(dlg.returnValue === "yes"); });
      dlg.returnValue = "no"; dlg.showModal();
    });
  }
  function openPanel(id) {
    S.lastFocus = document.activeElement;
    return api("GET", "/admin/users/" + id).then(function (d) { S.detail = d; renderPanel(); var p = $("#panel"); p.hidden = false; $(".panel-in", p).focus(); }).catch(fail);
  }
  function closePanel() { $("#panel").hidden = true; S.detail = null; if (S.lastFocus && S.lastFocus.focus) S.lastFocus.focus(); }
  function renderPanel() {
    var d = S.detail; if (!d) return;
    var self = S.me && S.me.id === d.id;
    $("#pAv").textContent = initial(d.display_name); $("#pName").textContent = d.display_name; $("#pMail").textContent = d.email;
    var badges = $("#pBadges"); clear(badges);
    badges.appendChild(h("span", { "class": "badge " + (d.is_active ? "ok" : "bad"), text: t(d.is_active ? "s.active" : "s.suspended") }));
    badges.appendChild(h("span", { "class": "badge" + (d.role === "admin" ? " admin" : ""), text: t("r." + d.role) }));
    if (d.is_demo) badges.appendChild(h("span", { "class": "badge demo", text: t("demo") }));
    if (self) badges.appendChild(h("span", { "class": "badge", text: t("you") }));
    var facts = $("#pFacts"); clear(facts);
    [["p.business", d.business_name || "–"], ["p.phone", d.phone || "–"], ["p.language", langName(d.language)], ["p.joined", fmtDate(d.created_at)], ["p.last", ago(d.last_active)],
     ["h.signins", nf(d.sign_ins)], ["h.brands", nf(d.brands)], ["h.products", nf(d.products)], ["p.sessions", nf(d.open_sessions)]].concat(d.role === "admin" ? [["p.secret", t(d.has_secret_word ? "yes" : "no")]] : []).forEach(function (r) { facts.appendChild(h("dt", { text: t(r[0]) })); facts.appendChild(h("dd", { text: r[1] })); });
    var act = $("#pActions"); clear(act);
    var mk = function (label, cls, fn, dis, ic) { return h("button", { type: "button", "class": "btn " + cls, disabled: dis, onclick: fn }, icon(ic), label); };
    act.appendChild(mk(t(d.is_active ? "act.suspend" : "act.reactivate"), d.is_active ? "danger" : "primary", function () { change(d.is_active ? "suspend" : "react"); }, self && d.is_active, d.is_active ? "i-ban" : "i-check"));
    act.appendChild(mk(t(d.role === "admin" ? "act.removeAdmin" : "act.makeAdmin"), "", function () { change(d.role === "admin" ? "remove" : "make"); }, self, "i-shield"));
    act.appendChild(mk(t("act.signout"), "", function () { change("out"); }, false, "i-out"));
    if (self) act.appendChild(h("p", { "class": "p-note", text: t("selfNote") }));
    var feed = $("#pFeed"); clear(feed);
    if (!d.recent_events.length) feed.appendChild(h("li", { "class": "empty", text: t("noEvents") }));
    feedItems(d.recent_events, false).forEach(function (li) { feed.appendChild(li); });
  }
  var ACTIONS = {
    suspend: { body: { is_active: false }, k: "c.suspend", toast: "t.suspend", danger: true, label: "act.suspend" },
    react: { body: { is_active: true }, k: "c.react", toast: "t.react", label: "act.reactivate" },
    make: { body: { role: "admin" }, k: "c.make", toast: "t.make", label: "act.makeAdmin" },
    remove: { body: { role: "user" }, k: "c.remove", toast: "t.remove", danger: true, label: "act.removeAdmin" },
    out: { out: true, k: "c.out", toast: "t.out", label: "act.signout" }
  };
  function change(kind) {
    var a = ACTIONS[kind], d = S.detail; if (!d) return;
    confirmDialog(t(a.k + ".t"), t(a.k + ".b", { n: d.display_name }), t(a.label), a.danger).then(function (ok) {
      if (!ok) return;
      var call = a.out ? api("POST", "/admin/users/" + d.id + "/sign-out") : api("PATCH", "/admin/users/" + d.id, a.body);
      return call.then(function () { toast(t(a.toast)); return Promise.all([openPanel(d.id), loadUsers(), loadOverview()]); }).catch(function (e) { toast(e.message || t("t.fail"), true); });
    });
  }

  /* ---------- CSV ---------- */
  function download(path, name) {
    api("GET", path, undefined, true).then(function (res) { return res.blob(); }).then(function (blob) {
      var a = document.createElement("a"), url = URL.createObjectURL(blob);
      a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
      toast(t("t.dl"));
    }).catch(function (e) { toast(e.message || t("t.fail"), true); });
  }

  /* ---------- loading and failure ---------- */
  function show(which) { ["denied", "error"].forEach(function (id) { $("#" + id).hidden = id !== which; }); $("#app").hidden = which !== "app"; }
  function fail(err) {
    if (err.status === 401 || (err.status === 403 && err.message === "Admin sign-in required.")) { window.location.href = "admin-login.html"; return; }
    if (err.status === 403 && !S.me) { show("denied"); return; }
    if ($("#app").hidden) { $("#errMsg").textContent = err.message; show("error"); } else toast(err.message || t("t.fail"), true);
  }
  function loadOverview() {
    return api("GET", "/admin/overview?" + qs(periodParams())).then(function (o) { S.overview = o; renderStats(); renderCharts(); }).catch(fail);
  }
  function loadAll() {
    return api("GET", "/users/me").then(function (me) {
      S.me = me;
      if (me.role !== "admin") { show("denied"); return; }
      $("#whoName").textContent = me.display_name; $("#whoAv").textContent = initial(me.display_name); $("#whoMail").textContent = me.email;
      show("app");
      return Promise.all([loadOverview(), loadUsers(), loadActivity()]);
    }).catch(fail);
  }
  function renderAll() { applyStatic(); renderStats(); renderCharts(); renderUsers(); renderActivity(); if (S.detail) renderPanel(); }

  /* ---------- wiring ---------- */
  function setPeriod(p) {
    S.period = p; $$("#period button").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-p") === p); });
    $("#customBox").hidden = p !== "custom";
    if (p !== "custom") { S.act.page = 1; loadOverview(); if (S.act.scope === "period") loadActivity(); }
  }
  function selectTab(name) {
    var users = name === "users";
    $("#tabUsers").setAttribute("aria-selected", String(users)); $("#tabActivity").setAttribute("aria-selected", String(!users));
    $("#paneUsers").hidden = !users; $("#paneActivity").hidden = users;
  }
  function route() {
    var hash = (location.hash || "#dashboard").slice(1);
    $$("[data-nav]").forEach(function (a) { a.classList.toggle("on", a.getAttribute("data-nav") === hash); });
    if (hash === "users" || hash === "activity") { selectTab(hash); var c = $("#tabsCard"); if (c && c.scrollIntoView) c.scrollIntoView({ block: "start" }); }
    closeMenu();
  }
  function closeMenu() { $("#side").classList.remove("open"); $("#scrim").hidden = true; $("#menuBtn").setAttribute("aria-expanded", "false"); }
  var debounce;
  function init() {
    $("#themeBtn").setAttribute("aria-checked", document.documentElement.getAttribute("data-theme") === "dark" ? "true" : "false");
    applyStatic();
    $("#themeBtn").addEventListener("click", function () { setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"); });
    $("#langBtn").addEventListener("click", function () { lang = lang === "bn" ? "en" : "bn"; store.set("adbanao-lang", lang); renderAll(); });
    $("#menuBtn").addEventListener("click", function () { var o = $("#side").classList.toggle("open"); $("#scrim").hidden = !o; this.setAttribute("aria-expanded", String(o)); });
    $("#scrim").addEventListener("click", closeMenu);
    $("#whoBtn").addEventListener("click", function () { var m = $("#whoMenu"); m.hidden = !m.hidden; this.setAttribute("aria-expanded", String(!m.hidden)); });
    document.addEventListener("click", function (e) { if (!e.target.closest(".who")) { $("#whoMenu").hidden = true; $("#whoBtn").setAttribute("aria-expanded", "false"); } });
    $("#signOutBtn").addEventListener("click", function () { api("POST", "/auth/logout").catch(function () {}).then(function () { window.location.href = "admin-login.html"; }); });
    $("#retryBtn").addEventListener("click", loadAll);
    $$("#period button").forEach(function (b) { b.addEventListener("click", function () { setPeriod(b.getAttribute("data-p")); }); });
    var today = new Date().toISOString().slice(0, 10), wk = new Date(Date.now() - 6 * 864e5).toISOString().slice(0, 10);
    $("#dStart").value = wk; $("#dEnd").value = today; $("#dEnd").max = today;
    $("#applyCustom").addEventListener("click", function () {
      S.start = $("#dStart").value; S.end = $("#dEnd").value;
      if (!S.start || !S.end || S.start > S.end) { toast(lang === "bn" ? "সঠিক শুরু ও শেষ তারিখ দিন।" : "Pick a start date that is not after the end date.", true); return; }
      loadOverview(); if (S.act.scope === "period") loadActivity();
    });
    $("#dlUsers").addEventListener("click", function () { var u = S.users; download("/admin/export/users.csv?" + qs({ q: u.q.trim(), status: u.status, role: u.role, language: u.language }), "adbanao-users.csv"); });
    $("#dlActivity").addEventListener("click", function () { download("/admin/export/activity.csv?" + qs(activityQuery()), "adbanao-activity.csv"); });
    $("#q").addEventListener("input", function () { clearTimeout(debounce); var v = this.value; debounce = setTimeout(function () { S.users.q = v; S.users.page = 1; loadUsers(); }, 250); });
    [["fStatus", "status"], ["fRole", "role"], ["fLang", "language"]].forEach(function (p) { $("#" + p[0]).addEventListener("change", function () { S.users[p[1]] = this.value; S.users.page = 1; loadUsers(); }); });
    $("#uPer").addEventListener("change", function () { S.users.per = +this.value; S.users.page = 1; loadUsers(); });
    $("#aGroup").addEventListener("change", function () { S.act.group = this.value; S.act.page = 1; loadActivity(); });
    $("#aPeriod").addEventListener("change", function () { S.act.scope = this.value; S.act.page = 1; loadActivity(); });
    $("#aPer").addEventListener("change", function () { S.act.per = +this.value; S.act.page = 1; loadActivity(); });
    $("#tabUsers").addEventListener("click", function () { selectTab("users"); });
    $("#tabActivity").addEventListener("click", function () { selectTab("activity"); });
    $("#panelClose").addEventListener("click", closePanel);
    $("#panel").addEventListener("click", function (e) { if (e.target === this) closePanel(); });
    $("#pViewAll").addEventListener("click", function () { var d = S.detail; if (!d) return; S.act.userId = d.id; S.act.userName = d.display_name; S.act.group = "all"; S.act.scope = "all"; $("#aGroup").value = "all"; $("#aPeriod").value = "all"; S.act.page = 1; closePanel(); selectTab("activity"); loadActivity(); $("#tabsCard").scrollIntoView({ block: "start" }); });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if (!$("#panel").hidden && !$("#confirm").open) closePanel(); else closeMenu();
    });
    var rz; window.addEventListener("resize", function () { clearTimeout(rz); rz = setTimeout(renderCharts, 150); });
    window.addEventListener("hashchange", route);
    loadAll().then(route);
  }
  init();
})();
