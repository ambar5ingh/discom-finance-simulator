# DISCOM Finance Simulator

An open-source policy simulator for the finances of India's electricity distribution companies (DISCOMs).
Move policy sliders for tariffs, subsidy payment, losses, true-ups, debt relief and demand, and see how the
cash gap, tariffs and balance sheet evolve to **FY2047-48** (Viksit Bharat) and **2070** (net zero).

The model splits each year's cash gap into the five causes identified by CSEP's *Breaking Down the Gap in
DisCom Finances* (2023): excess billing loss (**D**), consumer non-collection (**C**), unpaid subsidy
(**S**), deferred regulatory income (**RI**) and a **residual** (tariffs below cost). The FY2020-21 base year
reproduces CSEP's ₹1,04,091 crore gap exactly.

> Independent project. Not affiliated with or endorsed by any organisation cited in `data/sources.csv`.

## Repository layout
```
discom-finance-simulator/
├── discom_sim/            model engine (pure Python: pandas + numpy)
│   ├── model.py           equations, target tests, tariff solver
│   ├── scenarios.py       presets S0–S5 and where their values come from
│   └── io.py              data loading
├── app/app.py             Panel web app (sliders, charts, data and method tabs)
├── data/                  inputs; every row carries a source_id
│   ├── sources.csv        source register (G1 = the single government source)
│   ├── baseline_all_india_fy2021.csv
│   ├── anchors_fy2025.csv
│   ├── state_anchors_fy2025.csv
│   ├── calibration_series_csep.csv
│   └── templates/entity_baseline_template.csv
├── notebooks/             01 calibration · 02 scenarios · 03 adding a state
├── docs/                  methodology.md, research_spec.md
├── tests/test_model.py    checks the FY21 reproduction and model identities
├── scripts/build_web.py   builds the server-free browser version into site/
├── .github/workflows/deploy.yml   tests, builds and publishes to GitHub Pages
├── LICENSE (MIT, code) · DATA_NOTICE.md (data) · CITATION.cff
└── requirements.txt · pyproject.toml
```

## Run it on your computer
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                          # 5 tests should pass
panel serve app/app.py --show      # opens the app at http://localhost:5006/app
jupyter lab notebooks/             # the notebooks
```

## Publish it free on GitHub Pages
The published app runs entirely in the visitor's browser (Python via Pyodide), so it needs no server.

1. **Create the repository.** Sign in to GitHub with your personal account, click **New repository**,
   name it `discom-finance-simulator`, and set it to **Public**. Free Pages hosting on personal accounts
   needs a public repository. Don't add a README; this project already has one.
2. **Upload the files.** Choose one:
   - **Browser:** on the empty repository page, click *uploading an existing file*. Drag in the
     *contents* of the unzipped folder, not the folder itself, and commit to `main`. The web uploader
     can skip hidden folders, so check that `.github/workflows/deploy.yml` appears in the repository.
     If it is missing, use **Add file → Create new file**, type `.github/workflows/deploy.yml` as the
     name, and paste in its contents.
   - **Command line** (uploads everything, including hidden folders):
     ```bash
     cd discom-finance-simulator
     git init -b main
     git add .
     git commit -m "DISCOM Finance Simulator v0.1"
     git remote add origin https://github.com/<your-username>/discom-finance-simulator.git
     git push -u origin main
     ```
3. **Turn on Pages.** In the repository, go to **Settings → Pages** and set **Source** to **GitHub Actions**.
4. **Wait for the first build.** Open the **Actions** tab. The workflow runs the tests, builds `site/` and
   publishes it, which takes a few minutes. After that, the app is at
   `https://<your-username>.github.io/discom-finance-simulator/`.
   The first visit loads Python into the browser, so it takes a little while.

Every later push to `main` re-tests and republishes automatically.

### Build the browser version by hand (optional)
```bash
python scripts/build_web.py        # writes site/index.html and site/discom_finance_simulator.js
python -m http.server -d site 8000 # then open http://localhost:8000
```

## Rules for data contributions
- Each input row needs a `source_id` that exists in `data/sources.csv`.
- Official statistics come from one government source (`G1`); other sources are cited by name.
- Modelling assumptions are tagged `DESIGN` and must never be presented as facts.
- Store compiled figures with citations, not copied tables or text.

## Roadmap
1. Calibrate FY2021-22 to FY2024-25 using PFC utility reports and SERC true-up orders.
2. Add per-state and per-DISCOM baselines, starting with Tamil Nadu, Rajasthan, Maharashtra, Andhra Pradesh,
   Uttar Pradesh and Telangana (about two-thirds of DISCOM debt).
3. Add a power-procurement mix block (renewables, storage, thermal fixed charges) for the 2070 pathway.
4. Add real-terms (deflated) outputs and uncertainty ranges.

## Licence
Code: MIT (see `LICENSE`). Data: see `DATA_NOTICE.md`.
