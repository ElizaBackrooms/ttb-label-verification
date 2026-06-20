# TTB Alcohol Label Verification Assistant

**Standalone proof-of-concept prototype** — not production software. Built to demonstrate label verification workflows for evaluation and feedback.

Compare alcohol label application data to label artwork. Runs locally on your computer. **No API key required.**

> **Prototype — please read:** This is a **demonstration build**, not a finished TTB system. It does not connect to COLA, does not store your data, and uses local OCR instead of production-grade cloud vision. Accuracy on poor photos or unusual labels may require manual agent review. It is intended to show what is possible and gather feedback — not to replace human judgment today.

> **Performance note:** Analysis runs on **your computer**, not in the cloud. A **modern PC** typically processes one label in about **1–2 seconds**. An **older or slower machine** (e.g. aging office hardware) may take **3–5+ seconds per image** — that is normal and expected; there is no way to guarantee the same speed on every workstation. The app is still usable; it just reads and compares text locally. Large or high-resolution photos also take longer on any PC.

---

## Start here (everyone)

You do **not** need to be a developer. You do **not** need an API key.

### Windows — 3 steps

1. **Install Python** (one time)  
   Download from [python.org/downloads](https://www.python.org/downloads/)  
   During install, check **“Add python.exe to PATH”**.

2. **First-time setup** (one time)  
   Double-click **`setup.bat`** in this folder.  
   Wait until it says “Setup complete.”

3. **Open the app** (every time)  
   Double-click **`run.bat`**.  
   Your browser opens to **http://localhost:8501**

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

---

## Using the app (60 seconds)

**Single label**

1. Application fields are on the left (demo brand: `Stone's Throw`)
2. Upload a label photo in the middle
3. Click **Analyze Label** on the right

**Batch**

1. Open the **Batch Processing** tab
2. Download the CSV template
3. Upload your CSV + label images (or a ZIP)
4. Click **Run Batch Analysis**

---

## API keys

| Question | Answer |
|----------|--------|
| Do I need an API key to run this? | **No** |
| Does it send data to the cloud? | **No** — OCR runs on your computer |
| When would I need API keys? | Only if **you** add optional Azure/OpenAI features later |

Optional cloud settings (not used by default): copy `.env.example` to `.env` and add **your own** keys.

---

## What it does

- **Single label verification** — application data vs label photo
- **Batch processing** — CSV + many images (importer peak-season workflow)
- **Brand matching (Dave's rule)** — `Stone's Throw` vs `STONE'S THROW` = same brand
- **Government warning (Jenny's rule)** — exact 27 CFR 16.21 wording, all-caps bold header
- **Exports** — PDF and CSV reports
- **Private** — nothing saved after you close the app

---

## Run tests (optional)

Developers and reviewers can verify core logic:

```bash
python -m unittest tests.test_logic -v
```

Requires Tesseract for the synthetic OCR integration test (others run without it).

---

## Clone from GitHub (optional)

If you downloaded from GitHub instead of a ZIP:

```bash
git clone https://github.com/ElizaBackrooms/ttb-label-verification.git
cd ttb-label-verification
```

Then follow **Start here** above (`setup.bat` / `run.bat` on Windows).

---

## Manual setup (developers)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
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
├── setup.bat / run.bat       # Windows: double-click these
├── setup.sh / run.sh         # Mac/Linux
├── app.py                    # The application
├── requirements.txt          # Python packages
├── sample_batch_template.csv # Example batch CSV
├── .env.example              # Optional cloud keys (not required)
└── README.md                 # This file
```

---

## Approach and trade-offs

### Why these choices

- **Streamlit** — simple UI for agents with mixed tech comfort
- **Tesseract + OpenCV** — runs locally; no blocked cloud APIs on gov networks
- **Fuzzy + field-specific matching** — ABV/net parsed as numbers; brands allow caps-only differences
- **fpdf2** — PDF export without heavy infrastructure

### Stakeholder coverage

| Ask | Solution |
|-----|----------|
| Fast review (~5 sec) | Local OCR pipeline |
| Batch 200–300 labels | CSV + ZIP batch tab |
| Exact government warning | Word-for-word + caps + bold checks |
| Brand caps vs application | `Stone's Throw` ↔ `STONE'S THROW` |
| Bad photos | Auto deskew, contrast, denoise |
| Standalone PoC | No COLA integration; ephemeral |

### Limitations

- OCR quality depends on the photo
- Bold warning detection is best-effort
- Country of origin not yet in the form
- Cloud hosting needs Tesseract on the server — **local `run.bat` is the intended path**

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| “Python is not installed” | Install from [python.org](https://www.python.org/downloads/) with **Add to PATH** checked |
| “Tesseract not installed” | Run `winget install UB-Mannheim.TesseractOCR`, then restart `run.bat` |
| Batch image not found | Filename must match the `image_file` column in your CSV exactly |
| Browser didn’t open | Go to [http://localhost:8501](http://localhost:8501) manually |
| PDF export error | Run `setup.bat` again |

---

## Sample label fields

| Field | Example |
|-------|---------|
| Brand | `Stone's Throw` (app) / `STONE'S THROW` (label) |
| Class/Type | `Kentucky Straight Bourbon Whiskey` |
| ABV | `45% Alc./Vol. (90 Proof)` |
| Net contents | `750 mL` |
| Government warning | Standard 27 CFR 16.21 text (exact) |

---

Repository: [github.com/ElizaBackrooms/ttb-label-verification](https://github.com/ElizaBackrooms/ttb-label-verification)
