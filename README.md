# Bank Statement Processing and Classification System

Reads bank statement PDFs (text based or scanned), extracts account details and
transactions, classifies every transaction **without any LLM**, and exports to
Excel and CSV.

Full walkthrough: see the Build and Run Guide that came with this project.

---

## Quick start (five commands)

```bash
python run.py doctor                                 # what is installed
python run.py samples                                # make test statements
python run.py train                                  # train the classifier
python run.py process samples/sample_1_text_simple.pdf
python run.py ui                                     # optional browser view
```

Output lands in `output/`.

---

## Requirements

Python 3.10 or newer. **No third-party package is required.** The core runs on
the standard library alone, including a PDF text extractor written from
scratch, a Naive Bayes classifier, and an `.xlsx` writer.

Optional packages make it better:

```bash
pip install -r requirements-minimal.txt    # pdfplumber + openpyxl, recommended
pip install -r requirements.txt            # everything, including OCR and ML
```

Scanned PDFs additionally need the Tesseract **program** installed, not just
the Python binding. The guide covers this per operating system.

---

## What it does

| Stage | What happens |
|---|---|
| Read | pdfplumber, then pypdf, then the built-in reader |
| Detect | text or scanned, decided **per page**, so mixed files work |
| OCR | 300 DPI render, contrast stretch, deskew, Tesseract in table mode |
| Extract | account header, then the transaction table by column bands |
| Normalise | strip reference numbers and dates, find the counterparty |
| Classify | rules first, then a traditional ML model, then a review flag |
| Validate | balance continuity, duplicates, dates, opening and closing match |
| Export | Excel with five sheets, plus CSV |

### Classification is not an LLM

Two traditional layers:

1. **Heuristic rules** in `config/rules.json`. Editable regular expressions with
   priority, direction, channel and amount conditions. First match wins.
2. **A traditional ML model** for what rules miss. TF-IDF plus logistic
   regression when scikit-learn is installed, otherwise a multinomial Naive
   Bayes written in plain Python. Word n-grams plus character n-grams, so
   OCR damage and misspellings still classify.

Anything below the confidence floor stays `Uncategorised` and is flagged for
review, rather than guessed at.

---

## Project layout

```
run.py                     entry point for everything
run_tests.py               runs the test suite
config/rules.json          the editable rule pack
config/settings.json       optional overrides (created by you)
data/training_data.csv     seed training data
models/                    trained model, written by `train`
samples/                   generated test statements
output/                    exports land here

bsp/
  cli.py                   command line interface
  config.py                paths, settings, optional-package detection
  models.py                dataclasses passed between stages
  pipeline.py              the orchestrator
  normalize.py             narration cleaning, counterparty extraction
  validate.py              balance continuity and sanity checks
  pdfio/
    backends.py            pdfplumber / pypdf / built-in selection
    raw_pdf.py             the dependency-free PDF text extractor
    detector.py            text vs scanned, per page
    ocr.py                 render, deskew, Tesseract
  extract/
    patterns.py            dates, amounts, references, channels
    layout.py              words to lines, header detection, column bands
    account.py             account holder block
    transactions.py        the transaction table
  classify/
    taxonomy.py            the category list
    rules.py               heuristic rule engine
    naive_bayes.py         the built-in model
    sklearn_model.py       the optional model
    engine.py              hybrid decision logic
    train.py               training and evaluation
  exporters/               CSV and Excel
  samplegen/generate.py    sample statement generator
  ui/streamlit_app.py      browser interface

tests/                     35 tests, unit and end to end
tools/                     training data builder
```

---

## Common commands

```bash
# process a folder, plus one merged workbook
python run.py batch /path/to/statements --consolidate

# a password protected statement
python run.py process statement.pdf --password mypass

# force OCR even where a text layer exists (useful for bad text layers)
python run.py process statement.pdf --force-ocr --dpi 400

# see which rules fire for a narration
python run.py rules --explain "UPI/123/SWIGGY/swiggy@okaxis" --direction DR

# retrain after editing the training data
python run.py train --report output/model_report.json

# run the tests
python run_tests.py
```

---

## Deploying it

The browser interface can be hosted. Three routes, easiest first.

**Streamlit Community Cloud** (free, no card). Push this repo to GitHub, go to
share.streamlit.io, connect the repo, and set the main file to
`bsp/ui/streamlit_app.py`. It reads `requirements.txt` for Python packages and
`packages.txt` for the system packages OCR needs.

**Render.** Push to GitHub, then New, Blueprint, and point it at the repo.
`render.yaml` and `Dockerfile` do the rest. The free tier sleeps after
inactivity, so the first request takes about a minute to wake.

**Railway.** Push to GitHub, create a project from the repo. It detects the
`Dockerfile` automatically.

Vercel and Netlify are built for static sites and serverless functions, so they
do not suit a long-running Streamlit process. Use one of the three above.

The model is not committed to the repo, because a trained model is built from
data rather than shipped. The Dockerfile trains at build time, and the app
trains on first run if no model is present, so a fresh deploy works either way.

---

## Extending it

- **New merchant or category** → add a rule to `config/rules.json`, then
  `python run.py rules --test`. No retraining needed.
- **New category** → add it to `bsp/classify/taxonomy.py` first, then rules
  and training rows.
- **New bank layout** → add header synonyms to `bsp/extract/layout.py`, and
  date or amount formats to `bsp/extract/patterns.py`.
- **Better accuracy** → replace `data/training_data.csv` with your own labelled
  history and retrain. Real data beats the synthetic seed set every time.
