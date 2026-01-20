# Tundra Trait Team (TTT) Database Explorer

A lightweight Streamlit dashboard for exploring the **Tundra Trait Team (TTT)** trait database.  
It provides quick, interactive views of:

- **Species drill-down** (trait coverage, summary stats, distributions, measurement locations)
- **Trait overview** (top traits by coverage, distributions, time trends)
- **Spatial coverage** (global measurement locations, aggregated by geocoordinates)
- **Data quality** (missingness overview, `ErrorRisk` distribution and flagged record review)
- **Table view + export** (filter and download a subset as CSV)


## Setup

### Prerequisites

Make sure the following software is installed on your system:

- **Git**
  - Check:
    ```bash
    git --version
    ```
  - Install if needed: https://git-scm.com/downloads

- **Conda** (Miniconda or Anaconda)
  - Check:
    ```bash
    conda --version
    ```
  - Recommended: Miniconda (lighter weight)  
    https://docs.conda.io/en/latest/miniconda.html

- **Python**
  - Python does not need to be installed separately if you are using Conda.

---

### 1. Clone the repository

From a terminal:

```bash
git clone git@github.com:phchen5/ttt-dashboard.git
cd ttt-dashboard
```

### 2. Create the Conda environment

The project uses a Conda environment defined in `environment.yaml`.

```bash
conda env create -f environment.yaml
```

This will install all required dependencies (e.g., Streamlit, Altair, PyDeck, Pandas).

### 3. Activate the environment

```bash
conda activate ttt-dashboard
```

### Run the dashboard

From the repository root:

```bash
streamlit run app/app.py
```

On first run, the app will automatically download the Tundra Trait Team (TTT) dataset (if not already cached locally) and launch the dashboard in your browser.


