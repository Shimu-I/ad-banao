"""Makes the admin page call the API on the same host name as the page (like auth.js does).
Without this, signing in on 127.0.0.1 stores the cookie there, but the dashboard calls
localhost:8000 with no cookie and bounces back to the login page. Safe to run many times."""
from pathlib import Path

f = Path(__file__).resolve().parents[1] / "frontend" / "admin" / "admin.js"
old = 'var API = (window.ADBANAO_API || "http://localhost:8000").replace(/\\/$/, "");'
new = ('var API = (window.ADBANAO_API || "http://" + ((window.location.hostname && /^[\\w.\\-]+$/.test(window.location.hostname)) '
       '? window.location.hostname : "localhost") + ":8000").replace(/\\/$/, "");')
text = f.read_text(encoding="utf-8")
if old in text:
    f.write_text(text.replace(old, new), encoding="utf-8")
    print("OK  admin.js now follows the page host name.")
else:
    print("OK  admin.js already fixed." if "window.location.hostname" in text else "WARN  admin.js line not found; send it to Claude.")
