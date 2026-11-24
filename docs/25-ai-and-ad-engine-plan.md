# AI features, API foundations and the ad engine: options and plan

Status: **owner accepted option B on 2026-11-24** ([ADR 0007](adr/0007-ad-engine-ai-designer.md)). Still open: the free keys, and option C after A4. No code for this has been written yet. Written 2026-11-24 (Asia/Dhaka).

Goals covered: F8 (API foundations), A1 to A7 (ad engine), and where AI touches V1 to V6 (verification). Related: [03-tech-stack.md](03-tech-stack.md), [12-deployment-and-costs.md](12-deployment-and-costs.md), [15-risks.md](15-risks.md) (R-02, R-04), [07-roadmap.md](07-roadmap.md).

## 1. The question, in plain words

"Create the ad with AI, using free resources." That sentence hides four different jobs. Each has a different best answer:

| Job | What it means | Needs an AI model? |
| --- | --- | --- |
| 1. Write the words | Description, headline, offer line, in English and Bangla | Yes, a text model (already built, F6) |
| 2. Decide the design | Which template, colors, where text and photo go | Optional. Rules can do it, a text model can suggest it |
| 3. Draw the picture | Pixels: the photo, text, badges, background | Photo and text must be exact, so **no**. Only a decorative background could use an image model |
| 4. Check the ad | Prices, text, claims, photo unchanged | Mostly code and OCR. A model helps with claims and wording |

The product promise is "verified". That decides a lot: anything an image model draws cannot be verified by exact checks, and image models draw text badly and may alter the product.

## 2. Facts about free resources (checked 2026-11-24)

Free tiers change often. These come from the providers' own pages unless marked. Re-check before relying on any of them.

| Provider | What is free | Catch |
| --- | --- | --- |
| Google Gemini API, text | Many text models list a free tier ([pricing page](https://ai.google.dev/gemini-api/docs/pricing)), among them 2.5 Flash, 2.5 Flash-Lite and 3.5 Flash | Free-tier prompts and replies are used to improve Google's products. Limits vary by model and are shown in AI Studio, with no guarantee |
| Google Gemini API, **images** | **Nothing.** Nano Banana models and Imagen 4 show "Free tier: Not available" | Paid per image |
| **`gemini-2.0-flash` (our current default in code)** | **Shut down on 2026-06-01** per Google's pricing page | **A real Gemini call from today's code would fail.** Fixed in F8 by making the model a setting |
| Groq, text | Llama and other open models, about 30 requests per minute and 1,000 per day (OpenRouter's comparison, figures from April 2026, [source](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/)) | No training on your data, per that source. Unverified for Bangla quality. Figures are third-party, so check Groq's own page |
| Cloudflare Workers AI, images and text | 10,000 "Neurons" per day, reset 00:00 UTC ([pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)). FLUX.1 schnell costs 4.80 Neurons per 512x512 tile plus 9.60 per step | Needs a Cloudflare account and a small call from our server. My estimate with 4 steps: about 170 images a day at 1024x1024 or about 230 at 512x512. Context windows for text are small |
| Hugging Face Inference | **Free accounts get no credits.** PRO ($9 a month) includes $2 of credit | Not free. A thread shows FLUX.1-schnell was removed from its endpoint in July 2026, so models can vanish ([thread](https://discuss.huggingface.co/t/urgent-help-unusable-inference-credits-after-flux-1-schnell-removal/177901)) |
| Together AI, Replicate, OpenRouter (images) | Together: one-time $1 credit. Replicate: none. OpenRouter: no free images | Trials, not free tiers ([comparison, from a vendor that sells image infrastructure](https://www.runflow.io/blog/free-ai-image-generation-api-lies)) |
| Open-source on our own machine (Pillow, Tesseract, Ollama, Stable Diffusion) | Free software | Needs hardware. A laptop without a GPU is too slow for image models. Free hosting has no GPU |

Three consequences:
1. **There is no dependable free way to have an AI draw a whole ad image.** The only real free image option is Cloudflare, with a daily cap and a model that can disappear.
2. **Free text models are good enough** for words and layout suggestions, with a fallback chain.
3. **Pillow and Tesseract cost nothing** and give exact, checkable results. This is what the architecture already chose (decisions D-01 and D-02 in [03-tech-stack.md](03-tech-stack.md)).

## 3. Options for how the ad engine uses AI

### Option A. Templates only, AI writes the words

Pillow renders fixed templates. The text model writes copy. Layout comes from rules.

| Pros | Cons |
| --- | --- |
| Free, fast, works offline, deterministic | Ads can look samey |
| Fully verifiable: we know every pixel's source | No "AI designed it" story for the faculty |
| Original photo untouched (hash test) | More work to build several good templates |
| Bangla text shaping is under our control | |

### Option B. Templates plus a text model that proposes the design (recommended)

The model receives the product facts and returns a **scene** (JSON): which template, colors from the brand, headline, offer line, badge. Our code **validates** the scene (A1) and Pillow renders it. The model never touches pixels.

| Pros | Cons |
| --- | --- |
| Real AI value: varied copy, color choice, template choice | Needs rules to keep model output safe: schema check, color contrast check, fact check against the product |
| Still free (text tiers) and fully verifiable | Free-tier limits and outages, so a rule-based fallback must always work |
| Model output is data, so a bad answer is rejected, never shown | Model sees product data: free Gemini tier may train on it, so send no personal data and prefer Groq first |
| Same scene format the editor changes later (A6) | |

### Option C. Option B plus an AI-generated background (optional later)

The image model draws only a **background** (gradient, texture, scene). Our code puts the real photo, text and price on top.

| Pros | Cons |
| --- | --- |
| Visibly "AI made" and prettier ads | Only Cloudflare is truly free: about 170 per day, shared by all users, one model that could change |
| Product and text stay exact | Backgrounds can clash with the product, need contrast checks, can embed odd artifacts or fake text |
| Can be switched off with no loss | Slower (seconds per image). Needs storage and a copyright and safety review |

### Option D. Image model draws the whole ad (rejected)

| Pros | Cons |
| --- | --- |
| Least code | Garbled text, wrong prices, altered or invented product. This breaks the core promise and cannot be verified |
| | Nothing dependable is free |

### Option E. Our own GPU or a local model server

| Pros | Cons |
| --- | --- |
| No quotas, private | Needs a GPU we do not have. Free hosts have none. Not realistic for the first release |

**Recommendation: A first inside B, and C later behind a switch.** Build the renderer and scene format (A1 to A4) so that the ad works with no AI at all. Then add the text model as the designer (B). Add C only if there is time and the owner wants it.

## 4. Options for the provider layer (how the API talks to AI)

| Option | Pros | Cons |
| --- | --- | --- |
| 1. Keep our own thin adapters (today) | No new dependency, we see every call, easy to test with fakes | We maintain each adapter and re-check models ourselves |
| 2. A gateway such as OpenRouter or LiteLLM | One key, many models, built-in fallback | Another service in the middle, its own limits (OpenRouter free: about 50 requests a day), more privacy questions |
| 3. Use only one vendor's SDK | Simplest | One outage or limit change stops the product |

**Recommendation: option 1.** Keep the interface we have (`complete(prompt)`), add an `ImageProvider` interface beside it, and make every model name and key a **setting**. Revisit a gateway only if we outgrow two providers.

## 5. Plan, one goal at a time

Each step is one pull request with tests. Nothing needs a paid service. Steps marked **person** need the owner.

### F8. API foundations (first, small)

| Step | Change | How we test |
| --- | --- | --- |
| F8.1 | Model names and keys as settings. Replace the shut-down default with a configurable one. Verify the names against the live provider lists when the owner supplies a key (**person**) | Unit tests with fakes. Real call by the owner |
| F8.2 | One error format with a request ID on every response | API tests |
| F8.3 | Structured logging with the request ID, no secrets and no personal data in logs | Unit tests, a log-scrub test |
| F8.4 | `/health` checks database and lists which providers are configured, never showing keys | API tests |
| F8.5 | Provider call rules: timeout, retry once, a daily budget counter per provider, circuit breaker after repeated failures | Fake-provider tests |
| F8.6 | Add `/api/v1` prefix only if not already there. Check what exists first | API tests |

### A1 to A4. Scene, fonts, renderer, templates (no AI yet)

A1 scene schema, A2 fonts and fitting (Bangla through Raqm, risk R-04), A3 one template and size, A4 three templates and three sizes. **Claude can build and test all of this alone.** A **person** must look at the sample ads and judge the look and Bangla spelling.

### A5 to A7. Storage, editing, resize

Versions, storage interface, editing API, resize and replace photo. Claude alone, tested in CI.

### B. The AI designer (inside the A steps, after A4)

| Step | Change |
| --- | --- |
| B.1 | A prompt that turns product and brand facts into a scene proposal, in JSON |
| B.2 | Validate: schema (A1), allowed templates and colors, contrast, text fits, **every number and claim in the scene must come from the product data** |
| B.3 | Fallback: if the model fails or the scene is rejected, build the scene by rules. The user never sees an error for this |
| B.4 | Order of providers and budget from F8.5. Groq first for privacy, Gemini second |

### C. Optional AI background

`ImageProvider` with a Cloudflare FLUX adapter, a daily budget, a fallback to a plain gradient, contrast and "no text in background" checks. Off by default.

## 6. Where AI is allowed and not allowed

| Allowed | Never allowed |
| --- | --- |
| Suggest words, template, colors, layout | Change the user's photo or draw the product |
| Draw a decorative background (option C) | Decide a price, unit, offer or claim that is not in the product data |
| Help rewrite a flagged claim for the user to approve | Approve an ad. Only a human approves |
| Read an ad for a claim check (V-series) | Be the only check. Exact checks (hash, OCR compare, price compare) come first |

## 7. Privacy and safety

- Free Gemini traffic may be used by Google to improve products. Send **no** customer names, emails, phone numbers or secrets. Product facts only.
- Keys only in `.env` or host secrets. Never in code, logs, the browser or error messages.
- Cap input size and number of calls per user per day, so one person cannot use the shared free quota.
- Treat every model answer as untrusted input: parse, validate, escape. A model reply is never run as code or markup.
- Prompt injection: product text from a user goes into prompts. Keep user text in a delimited data section, validate the output against the schema, and never let a model answer choose a file path, URL or command.
- Generated images need a review step for unsafe content before any use. Another reason option C is optional.

## 8. Costs and limits we should expect

| Item | Free amount | What happens at the limit |
| --- | --- | --- |
| Text (Groq, Gemini) | Roughly 1,000 requests a day on Groq (third-party figure), Gemini varies by model | Switch to the other provider, then to rule-based text |
| Background images (Cloudflare) | About 170 a day at 1024x1024 (my estimate) | Plain gradient |
| Pillow, Tesseract | Unlimited | CPU time only |

Each ad needs about one text call. A few hundred ads a day fit the free text tiers. That is plenty for a faculty demo and a small pilot, and not enough for a public launch. The paid upgrade path is in [12-deployment-and-costs.md](12-deployment-and-costs.md).

## 9. Risks

| Risk | How we handle it |
| --- | --- |
| Free limits or models change again (it already happened: the default model was shut down) | Models are settings, health check shows state, fallback chain, rule-based mode |
| Free Bangla quality is weak | Test set of Bangla samples in the evaluation (S1), human review, keep English first |
| Model invents offers or claims | Scene validator checks against product data, verification re-checks |
| Daily quota used up by one user | Per-user daily cap |
| Cloudflare image model removed | Option C is optional and has a fallback |
| Owner has no keys yet | Everything works with fakes in CI. Real-key tryout is a **person** step |

## 10. Decisions for the owner

| # | Question | My recommendation |
| --- | --- | --- |
| 1 | Ad engine approach | A first, inside B. C later if time allows. Reject D |
| 2 | Provider layer | Keep our own adapters (option 1) |
| 3 | Order | F8, then A1 to A4, then the AI designer, then A5 to A7 |
| 4 | Will you create free keys for Groq and Gemini now? | Yes. Needed to confirm model names. Put them in `.env` only |
| 5 | Open a Cloudflare account for option C? | Not yet. Decide after A4 |
| 6 | Is it acceptable that free Gemini may train on product facts? | Yes if no personal data is sent. Otherwise Groq only |

## 11. What happens after you decide

1. Update the roadmap rows for F8 and A1 to A7 with the chosen approach.
2. Add a decision record in `docs/adr/` for the ad engine approach.
3. Start F8.1, one pull request at a time, as usual.

## Sources

- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) (free tiers, image generation not free, `gemini-2.0-flash` shut down 2026-06-01, free-tier data use)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) (limits are per model, shown in AI Studio, not guaranteed)
- [Cloudflare Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Hugging Face Inference Providers pricing](https://huggingface.co/docs/inference-providers/pricing)
- [Hugging Face thread on FLUX.1-schnell removal](https://discuss.huggingface.co/t/urgent-help-unusable-inference-credits-after-flux-1-schnell-removal/177901)
- [OpenRouter: free LLM APIs compared](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/) (third party, figures as of April 2026)
- [Runflow: free image generation APIs](https://www.runflow.io/blog/free-ai-image-generation-api-lies) (written by a vendor of paid image infrastructure)
