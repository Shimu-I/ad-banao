# The database as a story

This page explains the database the way a person lives it: one shop owner, from signing up to approving an ad, and which table each moment writes to. The column-by-column reference is [19-database.md](19-database.md). Everything here matches `backend/app/db/models.py` and the migrations in `backend/alembic/versions/`.

**Who is in charge:** the database lead (role D in [23-team-roles.md](23-team-roles.md)). Rules they enforce are at the end.

## The cast: eight tables

| Table | One line | Gets a new row when | Used by a page today? |
| --- | --- | --- | --- |
| `users` | A person with an account | Someone signs up | Yes |
| `user_sessions` | "This browser is signed in as this person" | Someone signs in | Yes |
| `activity_events` | The diary of what happened | Almost any action | Yes (admin page) |
| `brands` | A business identity: name, colors, fonts, logo | A user creates a brand | Yes (API; page comes later) |
| `products` | Something the brand sells, with price and photo | A user adds a product | Yes (API; page comes later) |
| `ads` | One ad made for a product | An ad is generated | **Not yet.** Table exists, no route writes to it |
| `verification_reports` | One run of the checks on one version of an ad | An ad is checked | **Not yet** |
| `verification_checks` | One line of a report: price, OCR, claims and so on | A report is made | **Not yet** |

The last three are built ahead so the ad engine and the checks can be added without changing the structure. Say that plainly if asked.

## The story of Rina

Rina Akter runs Rina's Pickles in Dhaka. She is one of the three demo users.

### Chapter 1: Rina signs up. Table `users`

She types her email, a password and her name. One row is added to `users`.

- Her email is saved in lower case and must be unique, so `Rina@x.com` and `rina@x.com` cannot become two accounts.
- Her password is **not** saved. Only `password_hash` is, a salted scrypt value. Anyone who reads the table still cannot sign in as her.
- `role` is `user` and `is_active` is true. No form can change the role.
- `language` is `bn`, so the pages greet her in Bangla.
- `created_at` and `updated_at` record when. A profile edit moves `updated_at`.
- `activity_events` gets a `signup` line about her.

### Chapter 2: Rina signs in. Table `user_sessions`

The server makes a long random token and puts it in her browser cookie. The database keeps **only the hash** of that token in `user_sessions`, with her `user_id` and an `expires_at` 14 days later.

- If someone copies the table, they hold hashes that cannot be turned back into working cookies.
- Sign out deletes the row. The browser may still hold the cookie, but it no longer matches anything.
- If the user were ever removed, their sessions go with them (`ON DELETE CASCADE`), because a session means nothing without a person.
- `admin_verified` is false for Rina. It only becomes true for an admin who signed in on the admin page with the secret word.
- `activity_events` gets a `login` line.

### Chapter 3: Rina creates her brand. Table `brands`

She enters the name Rina's Pickles, colors and fonts. A row is added to `brands`, and `brands.user_id` points to Rina's row in `users`. **That column is the owner mark.**

- Every brand route first asks "is `user_id` the signed-in person?". If not, the server answers "not found", as if the brand did not exist, so nobody can learn that other people's ids exist.
- Colors and fonts are lists, stored as JSON in the row. They are small and always read together with the brand, so a separate table would add joins and no benefit.
- Brands are **archived** (`is_archived`), never deleted. The link to `users` is `ON DELETE RESTRICT`, which means the database itself refuses to remove a user who still owns brands.

### Chapter 4: Rina adds a product. Table `products`

She adds Mango Pickle 500g. A row goes into `products`, and `products.brand_id` points to her brand. Notice there is **no** `user_id` on a product. Ownership flows through the brand: product, then brand, then user. One owner column to keep correct, not two.

- `price` is a fixed-decimal number with two places. `1299.00` is stored exactly, with no floating-point surprises. The page can show `৳1,299` and the database holds `1299.00`.
- `original_price` lets an offer show a crossed-out price.
- `unit` is stored cleaned: `0.5kg` becomes `500 g`.
- `key_features` and `allowed_claims` are JSON lists. `allowed_claims` is the list of promises the business may make, which the claim checker will use later.
- `image_path` points to the saved photo and `image_sha256` is its **fingerprint**. Later, if an ad's photo has a different fingerprint, we know the photo was changed.
- `ON DELETE RESTRICT` again: a brand with products cannot be deleted, so we archive.

### Chapter 5: an ad is made (planned). Tables `ads`, `verification_reports`, `verification_checks`

When the ad engine exists, one product can have many ads. `ads.product_id` points to the product.

- `status` walks through `draft`, `needs_fix`, `verified`, `approved`.
- `content_hash` is a fingerprint of the ad's text and picture, and it changes with every edit. When a human approves, the current fingerprint is copied into `approved_content_hash`. **An approval counts only while the two match.** Edit the ad after approving and the approval silently stops counting, which is how "every edit is checked again" is enforced in the data.
- Each check run adds one `verification_reports` row for one version of one ad. Each report has many `verification_checks`, one per module (price, OCR, claims, brand, integrity, quality). A check result is `verified`, `issue_found` or `cannot_verify`, with a message, a suggestion and the evidence (what was expected, what was found).
- Reports and checks are just results derived from the ad, so deleting an ad deletes them (`ON DELETE CASCADE`). The link from an ad to its product is `RESTRICT`.

### Chapter 6: the diary. Table `activity_events`

Every time Rina signs in, changes her profile or her password, or creates, edits or archives a brand or product, a line is added. Each line says what (`event_type`), a short `detail` such as the brand name, and when.

- `user_id` says who it is about. `actor_id` is filled when **someone else** did it, for example an admin who suspended her. That is how the log can say "Rina was suspended by the admin".
- Both links are `ON DELETE SET NULL`, not `CASCADE`. If a person were removed, the diary lines stay, only the name is blanked. History should outlive the person.
- A failed sign-in for an email that does not exist is logged with no user and no typed email, so strangers' addresses never land in the table.

### Chapter 7: the admin. Columns on `users` and `user_sessions`

The admin console adds three columns, no new table.

- `users.role` is `user` or `admin`. `users.is_active` is false when suspended. Suspending also deletes that person's sessions.
- `users.admin_secret_hash` holds the hash of the admin's secret word, empty for normal users.
- `user_sessions.admin_verified` marks sessions made on the admin sign-in page. The admin area accepts only those.

## The chain of ownership

```text
users ──< brands ──< products ──< ads ──< verification_reports ──< verification_checks
  │
  ├──< user_sessions      (CASCADE: removed with the person)
  └──< activity_events    (SET NULL: the diary survives)
```

`A ──< B` reads "one A has many B". To find out who owns an ad you walk **left**: ad, product, brand, user.

## What happens if something is deleted

| Link | Rule | Why |
| --- | --- | --- |
| `brands.user_id` to `users` | RESTRICT | The database refuses to remove a person who owns brands. We archive instead |
| `products.brand_id` to `brands` | RESTRICT | Same: protect the history |
| `ads.product_id` to `products` | RESTRICT | Same |
| `user_sessions.user_id` to `users` | CASCADE | A session is meaningless without its person |
| `verification_reports.ad_id` to `ads` | CASCADE | A report is a result derived from the ad |
| `verification_checks.report_id` to `verification_reports` | CASCADE | A check belongs to its report |
| `activity_events.user_id` and `actor_id` to `users` | SET NULL | History outlives the person |

## See it yourself in Adminer

Open http://localhost:8080, sign in (System PostgreSQL, Server `db`, user, password and database all `adbanao`), choose **SQL command** and run these after `make seed`. They are plain read-only queries. They were written from the models and **not yet run** against your database, so tell the database lead if one fails.

Rina's whole story in one table: her brand and product, joined through the owner chain.

```sql
select u.email, b.name as brand, p.name as product, p.price
from users u
join brands b on b.user_id = u.id
join products p on p.brand_id = b.id
where u.email = 'rina@demo.adbanao.test';
```

The password is not stored, only a hash:

```sql
select email, substr(password_hash, 1, 14) as start_of_hash from users order by id;
```

Who is signed in right now, and until when. There is no token here, only its hash:

```sql
select u.email, s.created_at, s.expires_at, s.admin_verified
from user_sessions s join users u on u.id = s.user_id order by s.id;
```

The diary, newest first, with who did it to whom:

```sql
select e.created_at, e.event_type, u.email as about, a.email as done_by_admin
from activity_events e
left join users u on u.id = e.user_id
left join users a on a.id = e.actor_id
order by e.id desc limit 15;
```

## What the database lead enforces

1. **Only migrations change the schema.** Every change is a model edit, a new file in `backend/alembic/versions/`, a test and an update to [19-database.md](19-database.md) and this page, in one pull request.
2. **No hand edits to real data.** Use the app or the admin page.
3. **Ownership is never skipped.** A new route that touches brands, products or ads must check the owner and have a test with two users.
4. **Archive, never delete** user data.
5. **Secrets stay hashed.** No password, session token or secret word is ever stored or returned in readable form.
6. Keep the migration round trip working: `alembic downgrade` and `upgrade` again, on SQLite and PostgreSQL (`./scripts/check_my_machine.sh --postgres`).

## Questions to be ready for

| Question | Short answer |
| --- | --- |
| Why does a product have no `user_id`? | Ownership flows through the brand, so there is one place to keep correct |
| Why store a hash of the session token? | A copied table cannot be used to sign in |
| Why RESTRICT and not CASCADE on brands? | A mistake must not wipe a business's work. We archive |
| Why JSON for colors and fonts? | They are small lists always read with their brand |
| Why are `ads` and the report tables empty? | Built ahead of the ad engine, on purpose. No page writes to them yet |
| How do you know the schema is right? | A test builds it from the migrations and checks it matches the models, on SQLite in CI and PostgreSQL on the owner's PC |
