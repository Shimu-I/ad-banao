# Frontend

Planned: React, TypeScript, Vite, Tailwind (goals U1 onward). Until then this folder holds plain
HTML pages with no build step.

| File | What it is |
| --- | --- |
| `auth/auth.js` | Small client for the account API (`window.AdBanaoAuth`) |
| `profile.html` | Signed-in profile page: read and update details, change password, sign out |
| `signin.html`, `signup.html` | Sign-in and sign-up pages (added when the owner's designs arrive) |

## Try it

```bash
# terminal 1: the API
make run
# terminal 2: the pages (the API allows http://localhost:5173)
cd frontend && python3 -m http.server 5173
```

Open http://localhost:5173/profile.html. Signed out visitors are sent to `/signin.html`.
To use another API address, set `window.ADBANAO_API = "https://..."` before loading `auth.js`.
