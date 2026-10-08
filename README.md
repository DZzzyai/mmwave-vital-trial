# mmwave-vital-trial
> Working‑trial deliverable for mm‑wave FMCW radar remote vital‑sign detection task.

This repository contains Task 1 literature survey, Task 2 classical signal‑processing implementation for vital‑sign extraction from radar phase displacement signal.

## Contents
1. Task 1: Literature survey (`literature_table.md`)
2. Task 2: Classical denoising & HR/RR estimation from mm‑wave radar signal (`code/task2_hybrid_pipeline.py`)

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
├─ code/
│   └─ task2_hybrid_pipeline.py   # Task2 main python script
├─ data/
│   ├─ Raw_1.xlsx
│   ├─ Raw_2.xlsx
│   ├─ Ground_1.xlsx
│   └─ Ground_2.xlsx
├─ outputs/          # auto‑generated output directory
│   ├─ metrics_result.csv         # aggregated evaluation metrics
│   ├─ window_estimates_*.csv      # per‑sliding‑window estimation results
│   ├─ simulation_result.csv      # synthetic simulation test results
│   └─ *.png figures               # time‑series, PSD, HR error plots
├─ literature_table.md            # Task‑1 literature survey template
├─ requirements.txt
└─ .gitignore


## Environment setup
Install dependencies:
```bash
pip install -r requirements.txt

## How to run Task2

1. Put 4 dataset xlsx files under `./data/`
2. Run the main script:
python code/task2_classical.py

All generated results will appear inside `./outputs/`.

## Key experimental observations

1. Respiratory‑rate (RR) estimation achieves acceptable performance for FFT, Harmonic‑suppression and VMD. SSA can recover respiratory component.
2. Heart‑rate (HR) extraction suffers two main interferences: **breathing harmonic leakage** and non‑periodic body‑motion artifacts.
3. Respiratory‑harmonic notch suppression brings measurable improvement on HR MAE and ±2 % valid‑window hit‑rate. It only suppresses breathing‑related harmonics and cannot eliminate random body‑motion noise.
4. Segment‑wise median post‑filter effectively suppress abrupt abnormal HR jumps, without generating interpolated fake values for long invalid segments.
5. SSA performs reasonably on RR estimation, but HR extraction degrades heavily on this dataset. Energy‑based SVD reconstruction tends to preserve high‑amplitude low‑frequency motion artifacts, while weak heart‑rate physiological components get overwhelmed.

## Limitations & Future improvements

1. VMD performance is sensitive to hyper‑parameters `K` and `alpha`. Mode selection based purely on frequency band and energy may discard weak but valid physiological modes.
2. SSA energy‑threshold reconstruction prioritizes high‑amplitude artifact components under heavy motion noise.
3. Mirror‑padding reduces notch‑filter boundary transient effect but cannot eliminate it completely.
4. Current dataset has no real IMU measurements. Future work: integrate IMU‑driven motion mask to discard high‑motion windows.
5. More synthetic test sequences can be added to further verify algorithm robustness under different SNR and harmonic strength.

## AI Conversation Records
