/* AdBanao auth client. No build step, no dependencies.
 *
 * Include on any page:  <script src="/auth/auth.js"></script>
 * Exposes window.AdBanaoAuth. The browser keeps the sign-in cookie (httpOnly), so this
 * code never sees or stores a password or token.
 */
(function () {
  "use strict";

  // Set window.ADBANAO_API before this script to point at another server.
  var API = (window.ADBANAO_API || "http://localhost:8000").replace(/\/$/, "");

  function message(body, status) {
    // FastAPI sends {detail: "text"} or, for validation, {detail: [{msg: "..."}]}.
    var d = body && body.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length) {
      return d.map(function (e) { return String(e.msg || "").replace(/^Value error, /, ""); })
              .filter(Boolean).join(" ");
    }
    return status >= 500 ? "Something went wrong on our side. Try again." : "Request failed.";
  }

  function request(method, path, data) {
    var opts = { method: method, credentials: "include", headers: {} };
    if (data !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(data);
    }
    return fetch(API + path, opts).then(function (res) {
      if (res.status === 204) return null;
      return res.json().catch(function () { return null; }).then(function (body) {
        if (!res.ok) {
          var err = new Error(message(body, res.status));
          err.status = res.status;
          throw err;
        }
        return body;
      });
    }, function () {
      throw new Error("Cannot reach the server. Check your connection and try again.");
    });
  }

  window.AdBanaoAuth = {
    signup: function (email, password, displayName, businessName) {
      return request("POST", "/auth/signup", {
        email: email, password: password, display_name: displayName,
        business_name: businessName || null,
      });
    },
    login: function (email, password) {
      return request("POST", "/auth/login", { email: email, password: password });
    },
    logout: function () { return request("POST", "/auth/logout"); },
    me: function () { return request("GET", "/users/me"); },
    updateProfile: function (fields) { return request("PATCH", "/users/me", fields); },
    changePassword: function (current, next) {
      return request("POST", "/users/me/password", { current_password: current, new_password: next });
    },
    /* Call on pages that need a signed-in user. Sends visitors to the sign-in page. */
    requireUser: function (signinUrl) {
      return window.AdBanaoAuth.me().catch(function (err) {
        if (err.status === 401) { window.location.href = signinUrl || "/signin.html"; }
        throw err;
      });
    },
  };
})();
