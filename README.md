# TTB Alcohol Label Verification Assistant

**Standalone proof-of-concept prototype** — not production software. Built to demonstrate label verification workflows for evaluation and feedback.

Compare alcohol label **application data** (what was submitted on the COLA form) to **label artwork** (what appears on the physical label photo). Runs locally on your computer by default. **No API key required** for default mode.

> **Want production-style cloud AI?** Scroll to **[Option B — Enhanced AI Mode](#option-b--enhanced-ai-mode)** for Azure Document Intelligence + vision LLM setup.

> **Prototype — please read:** This is a **demonstration build**, not a finished TTB system. It does not connect to COLA, does not store your data, and uses local OCR instead of production-grade cloud vision. Accuracy on poor photos or unusual labels may require manual agent review. It is intended to show what is possible and gather feedback — not to replace human judgment today.

> **Performance note:** Analysis runs on **your computer**, not in the cloud. A **modern PC** typically processes one label in about **1–2 seconds**. An **older or slower machine** (e.g. aging office hardware) may take **3–5+ seconds per image** — that is normal and expected. Large or high-resolution photos also take longer on any PC.

---

## Table of contents

- [Who this is for](#who-this-is-for)
- [Start here (everyone)](#start-here-everyone)
- [Using the app](#using-the-app)
- [Understanding results](#understanding-results)
- [What gets checked](#what-gets-checked)
- [Batch processing (CSV format)](#batch-processing-csv-format)
- [Analysis engine: local vs Option B](#analysis-engine-local-vs-option-b)
- [API keys and privacy](#api-keys-and-privacy)
- [Option B — Enhanced AI Mode](#option-b--enhanced-ai-mode)
- [How it works (technical overview)](#how-it-works-technical-overview)
- [Run tests (optional)](#run-tests-optional)
- [Manual setup (developers)](#manual-setup-developers)
- [Project files](#project-files)
- [Approach and trade-offs](#approach-and-trade-offs)
- [Troubleshooting](#troubleshooting)
- [Sample label fields](#sample-label-fields)

---

## Who this is for

| Audience | How to use this repo |
|----------|----------------------|
| **Compliance agents** | Double-click `setup.bat` once, then `run.bat` each time. See [Using the app](#using-the-app). Print `START_HERE.txt` for a one-page desk reference. |
| **Supervisors / reviewers** | Run the app on sample labels, review pass/review/fail output, export PDF or CSV reports from batch runs. |
| **Developers / evaluators** | Clone the repo, run [tests](#run-tests-optional), inspect `app.py` logic, optionally enable [Option B](#option-b--enhanced-ai-mode). |

**What this prototype demonstrates**

- Side-by-side comparison of application fields vs OCR-extracted label text
- Strict government warning validation (27 CFR 16.21 wording, header formatting)
- Brand-name tolerance for capitalization differences (Dave's rule)
- Single-label and batch workflows for peak-season volume
- Optional cloud AI path when local OCR is not enough

---

## Start here (everyone)

You do **not** need to be a developer. You do **not** need an API key for default mode.

### Windows — 3 steps

1. **Install Python** (one time)  
   Download from [python.org/downloads](https://www.python.org/downloads/)  
   During install, check **“Add python.exe to PATH”**.

2. **First-time setup** (one time)  
   Double-click **`setup.bat`** in this folder.  
   Wait until it says “Setup complete.”  
   Setup will offer to install **Option B** packages — say **N** unless you already have Azure/OpenAI keys.

3. **Open the app** (every time)  
   Double-click **`run.bat`**.  
   Your browser opens to **http://localhost:8501**  
   Keep the black command window open while you use the app. Close it (or press Ctrl+C) when finished.

If the app says Tesseract is missing, open PowerShell and run:

```
winget install UB-Mannheim.TesseractOCR
```

Then double-click **`run.bat`** again.

### Mac / Linux

```bash
chmod +x setup.sh run.sh
./setup.sh    # first time only
./run.sh      # every time
```

Install Tesseract if prompted:

- Mac: `brew install tesseract`
- Linux: `sudo apt install tesseract-ocr`

### Clone from GitHub

```bash
git clone https://github.com/ElizaBackrooms/ttb-label-verification.git
cd ttb-label-verification
```

Then follow the Windows or Mac/Linux steps above.

---

## Using the app

The app has two tabs: **Single Label** and **Batch Processing**.

### Choose an analysis engine

Below the header, expand **Analysis engine**:

| Mode | When to use |
|------|-------------|
| **Local OCR (default)** | No API key. Runs on your PC. Best for gov networks that block cloud APIs. |
| **Option B** | Requires `.env` keys. Sends label images to your Azure/OpenAI resources. |

The header subtitle updates to show which mode is active (local vs cloud).

### Single label workflow

1. **Left column — Application Data**  
   Enter what is on the COLA application (or use the pre-filled demo: brand `Stone's Throw`).

2. **Middle column — Label Image**  
   Upload a JPG or PNG photo of the label. A preview appears below the uploader.

3. **Right column — Analyze & Review**  
   Click **Analyze Label**. Results appear in the same column.

4. **Optional — Export PDF**  
   After analysis, use **Download PDF Report** for a printable summary.

**Tips for better photos**

- Shoot straight-on, not at a steep angle (the app auto-deskews mild tilt)
- Use even lighting; avoid heavy glare on foil or glass
- Include the full government warning block in frame
- Higher resolution helps small text, but very large files take longer to process

### Batch workflow

1. Open the **Batch Processing** tab.
2. Click **Download CSV template** (or copy `sample_batch_template.csv`).
3. Fill in one row per application — see [Batch CSV format](#batch-processing-csv-format).
4. Upload the CSV plus either:
   - Multiple image files, **or**
   - One ZIP file containing all images named in the CSV
5. Click **Run Batch Analysis**.
6. Sort/filter results, drill into any row, then **Export CSV** or **Export PDF**.

Batch uses the same **Analysis engine** selection as single-label mode.

---

## Understanding results

Each label gets an **overall status**:

| Status | Color | Meaning |
|--------|-------|---------|
| **Pass** | Green | Automated checks found no material issues. Still use judgment on edge cases. |
| **Review** | Yellow | Partial match or ambiguous OCR — agent should confirm manually. |
| **Fail** | Red | Likely rejection trigger (e.g. missing warning, wrong ABV, brand mismatch). |

Below the overall banner you will see:

- **Field Comparison** — table of entered vs extracted values with Match / Partial / Mismatch
- **Government Warning** — checklist for detection, all-caps header, bold header, exact wording
- **Expanders** — field match details, detected warning text, required exact text, raw OCR output

In **Option B** mode, an **Analysis engine** caption and optional **AI notes** from the vision LLM appear at the top of results.

---

## What gets checked

### Application fields compared

| Field | Matching behavior |
|-------|-------------------|
| **Brand name** | Case and punctuation tolerant — `Stone's Throw` matches `STONE'S THROW` (Dave's rule). Different brand names still fail. |
| **Class / Type** | Fuzzy text match; partial matches flagged for review. |
| **ABV / Proof** | Parsed as numbers — `45%` vs `45.0%` matches; `45%` vs `40%` fails. |
| **Net contents** | Normalized volume/units (e.g. `750 mL`, `750ml`). |
| **Bottler / producer** | Fuzzy text match on distillery name and location text. |

Match thresholds: **≥88%** similarity = Match, **≥72%** = Partial (review), below = Mismatch.

### Government warning (Jenny's rule — 27 CFR 16.21)

The app validates the **Surgeon General warning** against this exact text:

```
GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.
```

Checks performed:

1. **Detected** — warning block found in OCR text
2. **Header exact caps** — must read `GOVERNMENT WARNING:` in all capitals (not title case)
3. **Header bold** — best-effort ink-density check on the header region (may need manual confirm on unusual fonts)
4. **Wording exact** — ≥97% similarity to canonical wording; paraphrasing or missing clauses fails

Common rejection patterns this catches: title-case header, shortened warning text, OCR garble that changes meaning, warning buried in tiny type (may still flag for review).

### Not yet in scope

- Country of origin field
- COLA system integration or persistent case storage
- Barcode / QR verification

---

## Batch processing (CSV format)

Required columns (exact header names):

| Column | Description | Example |
|--------|-------------|---------|
| `application_id` | Your internal or COLA reference | `APP-001` |
| `brand` | Brand as entered on application | `Stone's Throw` |
| `class_type` | Class/type designation | `Kentucky Straight Bourbon Whiskey` |
| `abv` | Alcohol content line | `45% Alc./Vol. (90 Proof)` |
| `net` | Net contents | `750 mL` |
| `bottler` | Bottler statement | `"Old Tom Distillery, Louisville, KY"` |
| `image_file` | Filename only — must match uploaded file or ZIP entry | `stones_throw.jpg` |

**Rules**

- `image_file` is matched **by filename** (not full path). `stones_throw.jpg` and `folder/stones_throw.jpg` in a ZIP both match `stones_throw.jpg`.
- Quote bottler values that contain commas.
- Rows with missing images are skipped and listed under **Batch warnings**.
- See `sample_batch_template.csv` for two worked examples.

---

## Analysis engine: local vs Option B

| | **Local OCR (default)** | **Option B** |
|--|-------------------------|--------------|
| API key | Not required | Your Azure/OpenAI keys in `.env` |
| Where it runs | Your computer | Azure Document Intelligence + vision LLM |
| Network | Works offline after setup | Requires outbound HTTPS to your cloud endpoints |
| Speed | ~1–2 s/label (modern PC) | Network + API latency (often a few seconds) |
| Privacy | Images stay on device | Label JPEG sent to your cloud resources |
| Best for | Daily agent use, restricted networks | Production-style AI demos, hard OCR cases |

You can switch engines in the app without reinstalling. Default remains local.

---

## API keys and privacy

| Question | Answer |
|----------|--------|
| Do I need an API key? | **No** for default local mode |
| Does default mode send data to the cloud? | **No** — OCR and rules run on your PC |
| When do I need keys? | Only for **Option B** |
| Is data saved? | **No** — uploads and results are in memory only; closing the app clears them |
| Are keys stored in Git? | **No** — put keys in `.env` (gitignored); never commit `.env` |

---

## Option B — Enhanced AI Mode

**Optional upgrade path** for demos where cloud APIs are allowed. Combines:

1. **Azure Document Intelligence** (`prebuilt-read`) — high-quality OCR on label photos  
2. **Vision LLM** (Azure OpenAI or OpenAI) — structured field extraction, warning assessment, agent notes

Default **local mode** still works with no keys.

### Setup (Option B)

1. Complete normal setup (`setup.bat` or `setup.sh`).
2. Install Option B packages (or choose **Y** when `setup.bat` prompts):

   ```bash
   pip install -r requirements-option-b.txt
   ```

3. Copy `.env.example` to `.env` in the project root and fill in:

   ```env
   AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key

   # Preferred: Azure OpenAI
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your-key
   AZURE_OPENAI_DEPLOYMENT=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-08-01-preview

   # OR OpenAI directly (comment out Azure OpenAI lines above)
   # OPENAI_API_KEY=sk-...
   # OPENAI_VISION_MODEL=gpt-4o
   ```

4. Restart the app (`run.bat` / `run.sh`).
5. Expand **Analysis engine** → select **Option B — Azure Document Intelligence + Vision LLM**.
6. Analyze a label. Results show **Option B** as the engine and any LLM **AI notes**.

### What Option B sends to the cloud

| Data | Destination |
|------|-------------|
| Label image (JPEG) | Azure Document Intelligence, then vision LLM |
| Application fields + OCR text | Vision LLM prompt (not stored by this app) |
| API keys | Read from `.env` on your machine only |

**Cost:** You pay your own Azure/OpenAI usage. **Network:** Government environments that block external APIs should use **local mode**.

### Option B failure?

If analysis fails, check:

- `.env` file exists in the project root (same folder as `app.py`)
- Endpoint URLs have no trailing path errors
- Deployment name matches your Azure OpenAI resource
- Firewall allows HTTPS to Azure/OpenAI
- Error message in the app — it points to README and `.env`

---

## How it works (technical overview)

### Local mode pipeline

```
Label photo
  → OpenCV preprocess (deskew, CLAHE contrast, denoise, sharpen)
  → Tesseract OCR (multiple page-segmentation passes)
  → Field extraction (regex + fuzzy match against OCR lines)
  → Per-field comparison rules (brand, ABV, net, etc.)
  → Government warning validation (text + header bold heuristic)
  → Pass / Review / Fail + PDF/CSV export
```

### Option B pipeline

```
Label photo
  → Azure Document Intelligence OCR
  → Local field extraction (fallback merge)
  → Vision LLM JSON assessment (fields + warning + notes)
  → Same comparison UI and export formats
```

### Tech stack

- **UI:** Streamlit  
- **OCR:** Tesseract (+ OpenCV preprocessing) or Azure Document Intelligence  
- **Matching:** Python `difflib`, field-specific parsers  
- **PDF:** fpdf2  
- **Tests:** `unittest` in `tests/`

---

## Run tests (optional)

Developers and reviewers can verify core logic:

```bash
python -m unittest discover -s tests -v
```

**29 tests** cover brand matching, ABV parsing, warning validation, batch CSV/ZIP loading, PDF export, and Option B config/JSON helpers. One integration test requires Tesseract for a synthetic label image.

Optional timing benchmark:

```bash
python benchmark_timing.py
```

---

## Manual setup (developers)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
pip install -r requirements-option-b.txt   # optional
streamlit run app.py
```

| OS | Install Tesseract |
|----|-------------------|
| **Windows** | `winget install UB-Mannheim.TesseractOCR` |
| **macOS** | `brew install tesseract` |
| **Linux** | `sudo apt install tesseract-ocr` |

Set `TESSERACT_CMD` in `.env` if Tesseract is installed in a custom location (see `.env.example`).

---

## Project files

```
ttb-label-verification/
├── setup.bat / run.bat         # Windows: double-click these
├── setup.sh / run.sh           # Mac/Linux
├── START_HERE.txt              # Printable one-page quick start
├── app.py                      # Streamlit UI + local OCR pipeline
├── option_b_ai.py              # Option B: Azure DI + vision LLM
├── requirements.txt            # Python packages (local mode)
├── requirements-option-b.txt   # Optional cloud AI packages
├── sample_batch_template.csv   # Example batch CSV (2 rows)
├── benchmark_timing.py         # Optional per-label timing script
├── tests/
│   ├── test_logic.py           # Core matching, warning, batch, PDF tests
│   └── test_option_b.py        # Option B config and JSON tests
├── .env.example                # Template for Option B keys (copy to .env)
└── README.md                   # This file
```

---

## Approach and trade-offs

### Why these choices

- **Streamlit** — fast UI for agents with mixed tech comfort; no separate frontend build
- **Tesseract + OpenCV** — runs locally; no blocked cloud APIs on gov networks
- **Fuzzy + field-specific matching** — ABV/net parsed as numbers; brands allow caps-only differences
- **Strict warning checks** — encodes Jenny's compliance requirement in code
- **Option B module** — shows a credible production AI path without forcing cloud on every user
- **fpdf2** — PDF export without heavy infrastructure

### Stakeholder coverage

| Stakeholder ask | How this prototype addresses it |
|-----------------|----------------------------------|
| Fast review (~5 sec target) | Local pipeline ~1–2 s on modern hardware |
| Batch 200–300 labels | CSV + multi-file or ZIP upload, sortable results, CSV/PDF export |
| Exact government warning | Word-for-word + all-caps + bold header checks |
| Brand caps vs application | `Stone's Throw` ↔ `STONE'S THROW` treated as match |
| Bad photos | Auto deskew, contrast, denoise, sharpen before OCR |
| No cloud / no API keys | Default local mode; Marcus-friendly |
| Production AI demo | Option B with Azure DI + vision LLM |
| Standalone PoC | No COLA integration; ephemeral session data |

### Known limitations

- OCR quality depends on photo angle, lighting, and print size
- Bold warning detection is heuristic — unusual fonts may need manual review
- Country of origin not in the form yet
- Hosting on a shared server requires Tesseract there too — **local `run.bat` is the intended evaluation path**
- Option B requires you to provision and pay for your own Azure/OpenAI resources

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| “Python is not installed” | Install from [python.org](https://www.python.org/downloads/) with **Add to PATH** checked, then re-run `setup.bat` |
| “Tesseract not installed” | `winget install UB-Mannheim.TesseractOCR` (Windows), then restart `run.bat` |
| App opens but says setup required | Install Tesseract **or** configure Option B in `.env` |
| Analyze button disabled | Upload an image; for local mode, Tesseract must be installed |
| Batch image not found | `image_file` in CSV must **exactly** match uploaded filename (case-sensitive on Linux) |
| Batch row skipped | Check **Batch warnings** list for missing files or analysis errors |
| Browser didn’t open | Go to [http://localhost:8501](http://localhost:8501) manually |
| PDF export error | Re-run `setup.bat` to reinstall `fpdf2` |
| Option B “not configured” | Copy `.env.example` → `.env`, fill keys, restart app |
| Option B analysis failed | Verify endpoints, keys, deployment name, and network/firewall |
| Slow on old PC | Expected — see performance note at top; use smaller photos if needed |
| Port already in use | Close other Streamlit instances or restart the PC |

---

## Sample label fields

| Field | Example |
|-------|---------|
| Brand (application) | `Stone's Throw` |
| Brand (on label artwork) | `STONE'S THROW` ← still a **match** |
| Class/Type | `Kentucky Straight Bourbon Whiskey` |
| ABV | `45% Alc./Vol. (90 Proof)` |
| Net contents | `750 mL` |
| Bottler | `Old Tom Distillery, Louisville, KY` |
| Government warning | Full 27 CFR 16.21 text — see [What gets checked](#what-gets-checked) |

---

**Repository:** [github.com/ElizaBackrooms/ttb-label-verification](https://github.com/ElizaBackrooms/ttb-label-verification)

**Questions or feedback:** Open an issue on GitHub or share notes from your evaluation session — this prototype is meant to evolve from reviewer input.
