# AdBanao

**Create smarter. Verify better. Advertise confidently.**

AdBanao turns the details and photo a business enters once into a finished **image ad**, plus the **product description** and ad text. It then independently checks everything for accuracy, quality and brand consistency before publishing. The finished ad stays **editable**, and every edit is checked again.

> Status: early development. Built step by step; see [docs/PROGRESS.md](docs/PROGRESS.md) for what is done, what is not, and what has been tested. Workflow: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Full project plan, features, corner cases and costs: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md).

## The problem

Existing AI ad makers can change product appearance or packaging, generate wrong prices or invented benefits, produce generic content, and break brand consistency. Small businesses also write the product description, the ad text and the ad design separately, and an edited ad is never checked again. Businesses still review every ad by hand.

## The approach

1. The user fills in **one form**: product name, price and offer, key features, photo, brand colors and logo, language and ad size.
2. The AI writes the **product description**, headline, tagline and button text using only those facts.
3. The app builds the **ad as an image**. The original product photo is placed untouched on a template, with text, price badge and logo layered on top. The photo is never regenerated.
4. The ad is saved as **editable layers**. The user can move and resize items, edit text, change colors and fonts, switch template or size, and replace the photo. Every edit is a new version, so undo works.
5. **Checks run after generation and after every edit.** Each returns one of three results: **Verified**, **Issue found** or **Cannot verify**.
6. The user fixes issues, a human approves, and the final image and report are exported.

## MVP features

- One-form product and brand input with a guided, plain-language interface
- Product description and ad text generation, grounded in the entered facts
- Image ad creation from templates, original photo preserved, several sizes
- Editor for changing the ad after it is generated, with versions and undo
- Price and product detail verification
- OCR text checking of the exported image
- Unsupported claim detection (ad text and description)
- Brand consistency checking
- Explainable verification reports with one-click fixes

## Planned stack (free tiers first)

| Component | Technology |
| --- | --- |
| Frontend and editor | React, Tailwind CSS, a canvas library such as Konva |
| Backend | Python, FastAPI |
| Ad image rendering | Pillow |
| Database | PostgreSQL (Supabase or Neon free tier) |
| LLM | Gemini API, Groq (free tiers) |
| OCR | Tesseract |
| Vision | OpenCV, CLIP |
| ML | Scikit-learn, PyTorch |

## Repository layout

```
backend/    FastAPI app, database models, verification modules
frontend/   React and Tailwind web app and ad editor
tests/      Unit tests and the verification evaluation set
docs/       Project overview, progress log and contributing guide
```

## Getting started

Backend setup is in [backend/README.md](backend/README.md). Copy `.env.example` to `.env` and fill in your own keys. Never commit `.env`.

## Limitations

- Verification cannot guarantee 100% accuracy; a human approval step is always required.
- Creative quality is subjective and sales performance cannot be guaranteed.
- Product image similarity does not prove product identity.
- The editor covers basic edits only; it is not a full design tool.
- Free API tiers have rate limits that may change, and free AI writing is weaker in Bangla than in English.
- OCR quality is weaker for Bangla than for English.
