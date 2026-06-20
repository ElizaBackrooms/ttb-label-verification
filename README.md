# TTB Alcohol Label Verification Assistant

AI-powered prototype for comparing alcohol label application data against label artwork. Built for the Treasury take-home exercise: fast single-label review, batch importer workflows, strict government-warning checks, and agent-style brand matching.

## What it does

- **Single label verification** — enter COLA/application fields, upload a label photo, run analysis in seconds
- **Batch processing** — CSV of applications + multiple images or a ZIP
- **Field matching** — fuzzy comparison for brand, class/type, ABV, net contents, bottler
- **Brand judgment (Dave's rule)** — `Stone's Throw` on the application vs `STONE'S THROW` on the label is treated as the same brand (caps/punctuation only)
- **Government warning (Jenny's rule)** — word-for-word 27 CFR 16.21 text, `GOVERNMENT WARNING:` in all caps and bold
- **Exports** — PDF report (single/batch) and CSV (batch)
- **Ephemeral** — nothing is stored after the session ends

## Quick start (local — recommended)

### 1. Prerequisites

- **Python 3.11+**
- **Tesseract OCR** installed on your machine

This prototype uses **local OCR**. You do **not** need a cloud API key to run it.

| OS | Install Tesseract |
|----|-------------------|
| **Windows** | `winget install UB-Mannheim.TesseractOCR` or [UB-Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) |
| **macOS** | `brew install tesseract` |
| **Linux** | `sudo apt install tesseract-ocr` (Debian/Ubuntu) |

If Tesseract is not on your PATH, set `TESSERACT_CMD` in a `.env` file (see `.env.example`).

### 2. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/ttb-label-verification.git
cd ttb-label-verification

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501**

### 4. Try it

**Single label**

1. Leave the default brand as `Stone's Throw` (application side)
2. Upload a label image where the brand reads `STONE'S THROW`
3. Click **Analyze Label** — brand should show **Match**

**Batch**

1. Open the **Batch Processing** tab
2. Download the CSV template (or use `sample_batch_template.csv`)
3. Upload the CSV plus matching label images (filenames must match the `image_file` column)
4. Click **Run Batch Analysis**

## API keys — important

### Included prototype (this repo)

| Need API key? | Answer |
|---------------|--------|
| Run local OCR with Tesseract | **No** |
| Test single + batch flows | **No** |
| Export PDF/CSV reports | **No** |

### If you extend with cloud AI (optional, not included)

The README and code comments describe a production path using **Azure Document Intelligence** and **vision LLMs**. That is **not implemented** in this submission. If you fork and add cloud OCR or vision:

1. Copy `.env.example` → `.env`
2. **Use your own API keys** — none are provided in this repo
3. Never commit `.env` or secrets to GitHub

```bash
cp .env.example .env
# Edit .env with your own Azure/OpenAI credentials
```

Reviewers/evaluators: you can fully test the submitted prototype locally without any API keys. Cloud keys are only relevant if you add optional cloud services yourself.

## Project structure

```
ttb-label-verification/
├── app.py                      # Streamlit application
├── requirements.txt            # Python dependencies
├── sample_batch_template.csv   # Example batch input
├── .env.example                # Optional env vars (cloud extensions)
└── README.md
```

## Approach and trade-offs

### Technical choices

- **Streamlit** — fast PoC UI, accessible for agents with varying tech comfort
- **Tesseract + OpenCV** — runs fully local (important for gov networks that block outbound ML APIs)
- **Fuzzy matching + field-specific rules** — ABV/net parsed numerically; brand names allow presentation-only differences
- **fpdf2** — lightweight PDF export without a heavy reporting stack

### Requirements coverage

| Stakeholder ask | How we addressed it |
|-----------------|---------------------|
| Sarah — fast review | Local pipeline targets under ~5 seconds per label |
| Sarah / Janet — batch dumps | CSV + multi-image/ZIP batch tab with export |
| Jenny — exact warning | Word-for-word check, all-caps header, bold heuristic |
| Dave — brand judgment | `Stone's Throw` ↔ `STONE'S THROW` = Match |
| Jenny — imperfect photos | Deskew, contrast, denoise, sharpen before OCR |
| Marcus — standalone PoC | No COLA integration; ephemeral processing |

### Known limitations

- OCR accuracy depends on photo quality
- Bold detection on the warning header is heuristic, not typographic proof
- Font size / warning placement in fine print are not fully validated
- Country of origin (imports) is not in the comparison form yet
- Cloud deploy (Streamlit Cloud, etc.) requires Tesseract in the host image — **local run is the supported test path**

## Deployment note

This app depends on **Tesseract being installed on the host**. Most one-click Python hosts do not include it by default. For take-home review, please use the **local quick start** above.

If you deploy yourself (Docker/VM), install Tesseract in the image and set `TESSERACT_CMD` if needed.

## Sample label fields

Example distilled spirits label (from project brief):

| Field | Example |
|-------|---------|
| Brand | `OLD TOM DISTILLERY` / demo: `Stone's Throw` |
| Class/Type | `Kentucky Straight Bourbon Whiskey` |
| ABV | `45% Alc./Vol. (90 Proof)` |
| Net contents | `750 mL` |
| Government warning | Standard 27 CFR 16.21 text (exact) |

Use AI image tools or real label photos for additional test cases.

## Troubleshooting

**`TesseractNotFoundError`**

- Install Tesseract (see table above)
- Or set `TESSERACT_CMD` in `.env` pointing to your `tesseract` binary

**Batch row skipped — image not found**

- Ensure uploaded filenames match the `image_file` column exactly (e.g. `stones_throw.jpg`)

**PDF export fails**

```bash
pip install fpdf2
```

## License

Prototype for evaluation purposes.
