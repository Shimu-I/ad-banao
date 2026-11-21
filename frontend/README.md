# Frontend

Planned: React, TypeScript, Vite, Tailwind (goals U1 onward). Until then this folder holds plain
HTML pages with no build step.

| File | What it is |
| --- | --- |
| `auth/auth.js` | Small client for the account API (`window.AdBanaoAuth`) |
| `profile.html` | Signed-in profile page: read and update details, change password, sign out |
| `index.html` | Home page, with the sign-in and sign-up screens inside it (`#signin`, `#signup`). The forms call the API. After signing in, the header shows Profile and Sign out |
| `assets/img/` | Images used by `index.html` |

## Try it

```bash
# terminal 1: the API
make run
# terminal 2: the pages (the API allows http://localhost:5173)
cd frontend && python3 -m http.server 5173
```

Open http://localhost:5173/. Create an account from the page, then open Profile. Signed-out visitors to `profile.html` are sent to the sign-in screen.

Note: `index.html` loads Tailwind and fonts from public CDNs. That is fine for a prototype and is replaced when the React frontend is built (goal U1).
To use another API address, set `window.ADBANAO_API = "https://..."` before loading `auth.js`.
