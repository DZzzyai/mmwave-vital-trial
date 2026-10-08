# mmwave-vital-trial
> Working‑trial deliverable for mm‑wave FMCW radar remote vital‑sign detection task.

This repository contains Task 1 literature survey, Task 2 classical signal‑processing implementation for vital‑sign extraction from radar phase displacement signal.

## Contents
1. Task 1: Literature survey (`Task1_literature_table_and_summary.pdf`)
2. Task 2: Classical denoising & HR/RR estimation from mm‑wave radar signal (`code/task2_classical.py`)

---

# Task 2 Overview
Implemented algorithms for heart‑rate (HR) and respiratory‑rate (RR) extraction from FMCW mm‑wave radar phase signal:
1. Band‑pass filter + Welch‑FFT peak‑search (baseline)
2. VMD (Variational Mode Decomposition): energy‑weighted mode selection
3. SSA (Singular‑Spectrum Analysis): adaptive SVD energy‑ratio component reconstruction
4. Respiratory‑harmonic notch suppression: mirror‑edge padding to mitigate filter transient artefacts

Additional engineering features:
- Sliding‑window time‑series estimation
- Window‑level validity check for non‑finite / low‑variance segments
- Segment‑wise median post‑filter: avoid fake interpolated values for NaN segments
- Synthetic simulation module: reproduce breathing‑harmonic interference scenario described in task requirement
- Full quantitative metrics: MAE, RMSE, MAPE, ±2 % hit‑rate, Pearson correlation coefficient
- All outputs auto‑saved to separated `outputs/` folder, including aggregated metrics, window‑wise estimates, time‑series & error plots.

## Dataset
- `Raw_1.xlsx` / `Ground_1.xlsx`: Resting subject radar signal + ground‑truth reference
- `Raw_2.xlsx` / `Ground_2.xlsx`: Signal with motion‑artifact / apnea scenario + ground‑truth reference

> Radar sampling rate: **333.3333 Hz**
> Ground truth contains synchronized ECG / PPG / respiration reference and per‑sample HR/RR labels.

## Project folder structure
```bash
├─ code/
│   └─ task2_classical.py   # Task2 main python script
├─ data/
│   ├─ Raw_1.xlsx
│   ├─ Raw_2.xlsx
│   ├─ Ground_1.xlsx
│   └─ Ground_2.xlsx
├─ outputs/          # auto‑generated output directory
│   ├─ metrics_result.csv         # aggregated evaluation metrics
│   ├─ simulation_result.csv      # synthetic simulation test results
│   ├─ window_estimates_Apnea.csv # per‑window estimates for apnea case
│   ├─ window_estimates_Resting.csv # per‑window estimates for resting case
│   ├─ task2_Apnea.png            # HR/RR & PSD plot (Apnea)
│   ├─ task2_Resting.png          # HR/RR & PSD plot (Resting)
│   ├─ task2_error_Apnea.png      # HR estimation error curve (Apnea)
│   └─ task2_error_Resting.png    # HR estimation error curve (Resting)
├─ Task1_literature_table_and_summary.pdf            # Task‑1 literature survey template
├─ requirements.txt
└─ .gitignore
```

## Environment setup
Install dependencies:
```bash
pip install -r requirements.txt
```
