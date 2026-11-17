# Progress log

Last updated: 2026-11-18 (Asia/Dhaka). This file is updated in every step's pull request.

## How far are we

**4 of 14 build steps are done and merged (about 29%).** The steps still ahead include the largest pieces (ad generation, the editor, verification and the screens), so the real share finished is smaller than the step count suggests.

| Part of the product | State |
| --- | --- |
| Project structure and docs | Done |
| Backend foundation (app, settings, database models) | Done, never run against a real server (see testing below) |
| Product and brand profiles (input, photo upload, price and unit cleanup, readiness report) | Done in code, API never run |
| Product description and ad text generation | Done in code: key features, AI writing behind a swappable layer, fact checking, basic-text fallback. Never tried with a real Gemini or Groq key |
| Image ad creation | Not started |
| Editing the ad | Not started |
| Verification (prices, OCR, claims, brand, photo) | Not started |
| Reports, approval, export | Not started |
| Screens (guided form, editor, check panel) | Not started |
| Evaluation and deployment | Not started |

**What a user can do today:** nothing visual. There are no screens yet and no ads can be generated. The only way to try the code is the backend's built-in `/docs` page after starting the server on your own machine.

## Steps

| # | Step | Status | Merged in | Tested by Claude | Tested by you |
| --- | --- | --- | --- | --- | --- |
| 1 | Repo setup | Done | Pushed as the default branch | Files only; no code to test | Not reported |
| 2 | Backend skeleton and database models | Done | PR #2 | Code compiles; 6 database-URL tests pass; model and health tests written but never run | Not reported |
| 3 | Product and brand profiles | Done | PR #3 | 213 tests pass for the logic; API and model tests written but never run | Not reported |
| 4 | One-form brief and grounded generation | Done | This step's pull request | 28 new tests pass (fact checking, prompt, reply parsing, provider fallback, basic text); the new API route and its 6 tests were never run; no real AI service was called | Not reported |
| 5 | Ad design and image renderer | Not started | | | |
| 6 | Ad editing API | Not started | | | |
| 7 | Verification: prices and details | Not started | | | |
| 8 | Verification: OCR | Not started | | | |
| 9 | Verification: unsupported claims | Not started | | | |
| 10 | Verification: brand and image integrity | Not started | | | |
| 11 | Reports, one-click fixes, approval, export | Not started | | | |
| 12 | Frontend: guided form, editor, check panel | Not started | | | |
| 13 | Test set and evaluation | Not started | | | |
| 14 | Deployment and docs | Not started | | | |

Existing databases need the new `key_features` column: delete the local `adbanao.db` file and let the app recreate it (there is no data worth keeping yet), or add the column by hand.

Other work merged: project overview document (PR #1), rename to AdBanao (PR #4), faculty changes and this log (the pull request that added this file).

## Testing

### Run by Claude, in Claude's own environment (2026-11-16)

245 tests pass. They cover logic that does not need a web server or database.

| Area | Tests | Result |
| --- | --- | --- |
| Database URL helper | 6 | Pass |
| Price, discount and unit parsing | 119 | Pass |
| Photo validation and storage | 19 | Pass |
| Readiness checks | 28 | Pass |
| Request and response schemas | 45 | Pass |
| Fact checking of generated text | 12 | Pass |
| Text generation logic (with fake AI providers) | 16 | Pass |
| **Total** | **245** | **Pass** |

### Written but never run by anyone, as far as has been reported

These 3 files need packages that Claude's environment cannot install (FastAPI, SQLAlchemy and similar), so they were skipped there.

| Area | Test functions | Why it matters |
| --- | --- | --- |
| Database models | 8 | Checks the archive rule, approval expiry and the three-state result against a real database |
| Health endpoints | 2 | Checks the server starts and reaches the database |
| Brand and product API (includes the new generate-copy route) | 31 | Checks every route: create, edit, archive, photo upload, readiness |

Counted by test function; tests with several cases count once. **The API routes and the database models have been compiled and cross-checked but never executed.** A failure on your machine is possible and would be fixed in the next step.

### Not tested at all yet

- Real PostgreSQL (Supabase or Neon)
- Photo upload through a browser or the API
- Gemini and Groq with a real key (the code is written, but only fake providers were used in tests)
- Any screen or browser behavior (not built yet)
- Bangla text rendering and OCR (not built yet)

### Tested by you

**Nothing reported yet.** As far as this chat shows, you created and renamed the GitHub repository, connected GitHub, and looked at the repository page (screenshots on 2026-11-13 and 2026-11-16). That checks the files arrived, not that the code works.

Tick what you have run yourself, and write the result next to it. Tell Claude, or tick the same list in the project document, and it will be copied here.

- [ ] Install: `pip install -r backend/requirements-dev.txt`
- [ ] Run `pytest` from the repository root. Result (passed / failed / skipped): ______
- [ ] Start the server: `cd backend` then `uvicorn app.main:app --reload`, and open http://localhost:8000/docs
- [ ] Create a brand using `/docs`
- [ ] Create a product with price `৳1,299` and unit `0.5kg`. Check it comes back as `1299.00` and `500 g`
- [ ] Upload a product photo. Check it is accepted and any warnings make sense
- [ ] Open `GET /products/{id}/readiness` and check it lists what is missing
- [ ] Try bad input: price `12,99` and a PDF as the photo. Check the error messages are clear
- [ ] (Optional, step 4) Put a free Gemini or Groq key in `.env`, create a product with key features, and call `POST /products/{id}/generate-copy`. Check the text uses only your facts and `source` is `gemini` or `groq`
- [ ] (Optional) Connect a free Supabase or Neon database through `.env`

## Approvals

| Date | Approval | Scope |
| --- | --- | --- |
| 2026-11-16 | Owner wrote "i approve all and everyting" in chat (13:26, repeated 18:47, Asia/Dhaka) | The revised plan with the faculty changes, and all work merged so far: steps 1 to 3, the project overview, the rename to AdBanao |

Recorded as the owner's statement in chat. It is an approval of the direction and the merged work, not a record of reviewing the code line by line, and it does not replace the testing checklist above.

Earlier instructions from the owner: merge pull requests #1 and #2 (2026-11-13); after each update, pull and merge (2026-11-16).

## Decisions

| Date | Decision |
| --- | --- |
| 2026-11-13 | Build on free resources first. Move to paid services only if the MVP proves itself. |
| 2026-11-13 | Build one step at a time, with a plan shown first. |
| 2026-11-13 | Every check returns Verified, Issue found or Cannot verify. Never a forced pass. |
| 2026-11-13 | The original product photo is never regenerated or altered. |
| 2026-11-16 | Renamed the project from AdGuard AI to AdBanao. The GitHub repository is now `ad-banao`. |
| 2026-11-16 | After each step is pushed, open the pull request, merge it and pull. |
| 2026-11-16 | Faculty feedback adopted: the ad is an image generated from the user's details, product information and photo. One form also writes the product description. The ad can be edited after it is made. The interface must be user friendly. |
| 2026-11-16 | No AI-generated product imagery for now. It could change how the product looks. It stays on the "later" list as optional backgrounds. |

## Open items and risks

- The default branch is still named `step-01-repo-setup`. Rename it to `main` in the repository settings.
- The name AdBanao has not been checked for existing companies, trademarks or domain availability.
- The API routes and database models have never been run (see Testing).
- Claude's environment cannot install packages, so the React frontend and editor cannot be built or run there. They will need testing on your machine.
- Free AI services have rate limits, and Bangla output will be weaker. Step 4's basic-text fallback is in place.
- The editor preview in the browser may differ slightly from the exported image. The exported image is final and is the one that gets verified.
- Not handled yet: two people editing the same record at once, cleaning up unused photo files, and serving uploaded images over HTTP.

## History

| Date | What happened |
| --- | --- |
| 2026-11-13 | Idea reviewed. Project document written with features, corner cases, limits and costs. |
| 2026-11-13 | Step 1 pushed (repo setup). |
| 2026-11-13 | Step 2 built and merged (PR #2). Project overview added (PR #1). |
| 2026-11-16 | Step 3 built and merged (PR #3). |
| 2026-11-16 | Project renamed to AdBanao (PR #4). Repository renamed to `ad-banao` by the owner. |
| 2026-11-16 | Faculty feedback applied to the plan, the overview, the README and the contributing guide. This progress log added. |
| 2026-11-18 | Step 4 built: key features field, fact checking of generated text, Gemini and Groq providers with basic-text fallback, and the generate-copy route. |
