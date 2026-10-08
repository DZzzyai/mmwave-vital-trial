# Task2 Answers to Analysis Questions.md

## Implemented Methods
Four classical signal‑processing methods are implemented for heart‑rate(HR) and respiratory‑rate(RR) extraction from mm‑wave radar phase‑displacement signal:
1. Band‑pass filtering + Welch‑FFT peak‑picking (baseline)
2. VMD (Variational Mode Decomposition)
3. SSA (Singular‑Spectrum Analysis)
4. Respiratory harmonic notch suppression

Intermediate time‑domain waveforms and power‑spectral‑density(PSD) plots are auto‑generated in the outputs folder. Metrics including MAE, RMSE, MAPE and ±2 % hit‑rate are computed for Resting and Apnea/motion‑artifact test cases.

### Method strengths & failure modes (focus on respiratory‑harmonic interference)
1. **Band‑pass + FFT**
Strength: Simple, low computational cost. Works well under clean resting conditions.
Failure mode: Directly selects the strongest spectral peak inside target frequency band. **Respiratory harmonics or motion artifacts often produce higher PSD amplitude than real heartbeat**, causing large HR estimation error.

2. **VMD**
Strength: Adaptive mode decomposition, can separate respiration and heartbeat when signal‑to‑noise ratio is acceptable.
Failure mode: Sensitive to hyper‑parameters `K` and `alpha`. Under strong motion artifacts, mode‑mixing occurs. Motion‑related components may overwrite physiological modes. Cannot fundamentally solve harmonic leakage.

3. **SSA (Singular‑Spectrum Analysis)**
Strength: Good at extracting large‑amplitude respiratory component.
Failure mode: SVD reconstruction prioritizes high‑energy signal components. Motion artifacts have larger amplitude than weak heartbeat. Heartbeat component gets suppressed, leading to bad HR performance under motion.

4. **Respiratory harmonic notch suppression**
Strength: Targeted mitigation for respiratory‑harmonic leakage. It estimates base respiratory frequency and applies notch filters on its 2nd/3rd/4th harmonics before HR calculation. Validated both in synthetic simulation and real radar data.
Failure mode: Performance depends on accurate RR estimation. If respiratory frequency estimation drifts, notch filter may corrupt genuine heartbeat components. This method cannot handle random body‑motion noise.

## Proposed hybrid pipeline: wearable (PPG+IMU) to mm‑wave radar transition scenario
Drawing on prior PPG‑IMU wearable engineering experience and the adaptive IMU motion‑artifact cancellation study, this practical hybrid pipeline transfers wearable‑system knowledge to contact‑free mm‑wave radar, tackling both respiratory‑harmonic leakage and body‑motion artifacts.

1. **Adaptive IMU motion‑artifact pre‑processing**
When torso‑mounted IMU (accelerometer + gyroscope) measurements are available:
- For each sliding window, compute power spectra of radar phase signal, tri‑axial accelerometer and tri‑axial gyroscope.
- Instead of always using accelerometer or gyroscope as fixed noise reference, **dynamically select the proper IMU reference by comparing dominant spectral peak frequencies**.
- Perform frequency‑domain spectral‑subtraction motion‑artifact cancellation only under safe conditions. If artifact spectral peak overlaps the potential heart‑rate band, skip cancellation to avoid removing genuine heartbeat components.
- If IMU data is absent, skip this step and proceed with pure radar‑signal processing.

2. **Radar‑specific signal processing for valid windows**
After IMU pre‑processing on low‑risk windows:
- Apply VMD decomposition to separate signal components.
- Run respiratory‑harmonic notch suppression: estimate fundamental respiratory frequency and apply notch filters to its 2nd / 3rd / 4th harmonics falling within HR band, mitigating radar‑specific respiratory‑harmonic leakage.

3. **Sliding‑window post‑processing**
Apply segment‑wise median filter to suppress abrupt HR outliers. Long invalid NaN segments are not interpolated, preventing artificial fake physiological values.

4. **PPG auxiliary cross‑validation (hybrid co‑existence case)**
If PPG wearable is available alongside radar: use PPG‑estimated HR as auxiliary reference. Mark radar output as low‑confidence when estimation deviation is large.

5. **Confidence‑aware output**
Only output RR / HR under high overall confidence. Suppress results rather than reporting unreliable estimates.

> Transition note: In wrist‑PPG devices IMU captures wrist swing; for mm‑wave radar the IMU captures torso body movement. The adaptive spectral‑selection logic can be reused, but the physical source of motion signal differs. Respiratory‑harmonic leakage is a key challenge unique to radar phase‑displacement signals and is generally not present in wrist‑PPG systems.
