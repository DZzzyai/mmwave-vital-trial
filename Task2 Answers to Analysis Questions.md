# Task2 Answers to Analysis Questions

## Q1 What are the two main noise/interference sources for mm‑wave radar vital‑sign extraction in this dataset?
**Answer:**
1. **Breathing harmonic leakage**: Multiples of respiratory frequency fall within the heart‑rate frequency band. The higher‑amplitude breathing harmonics can override real heart‑rate peaks on the PSD spectrum, leading to wrong HR estimation.
2. **Non‑periodic body‑motion artifacts**: Random body movement introduces strong low‑frequency noise. Motion artifacts have large signal energy and easily overwhelm the weak heartbeat component in radar phase signal.

## Q2 Why does raw FFT produce poor heart‑rate results under interference?
**Answer:**
Raw FFT‑peak picking simply selects the maximum power peak inside the heart‑rate frequency range. When breathing harmonics or motion artifacts create stronger spectral peaks than real heartbeat, FFT will pick the interference peak instead of genuine heart frequency, resulting in large HR error.

## Q3 What principle does the harmonic‑suppression method use, and what are its limitations?
**Answer:**
- Principle: Estimate the fundamental respiratory frequency first, then apply notch filters to remove its 2nd / 3rd /4th breathing harmonics which fall into HR band, before heart‑rate estimation.
- Limitations:
  1. Depends on accurate respiratory‑rate estimation. If RR estimate is wrong, notching will corrupt useful heart‑rate signal.
  2. It can only eliminate breathing‑related harmonics, **cannot suppress random body‑motion noise**.

## Q4 Explain the performance difference observed for VMD / SSA on this dataset
**Answer:**
- VMD: Performance is highly sensitive to hyper‑parameter `K` and `alpha`. It can separate respiration and heartbeat when SNR is good, but under heavy motion artifacts, mode‑mixing occurs; strong artifact components may occupy valid physiological modes.
- SSA: Works well for extracting respiratory component (large amplitude). However SVD energy‑based reconstruction prioritizes high‑amplitude motion artifacts. Weak heartbeat component gets overwhelmed, leading to bad HR results under motion.

## Q5 Why do we add median post‑processing after sliding‑window estimation?
**Answer:**
Sliding‑window estimations may produce sporadic sharp jump outliers caused by spectrum mis‑pick. Segment‑wise median filter suppress these abrupt abnormal HR values. In our implementation we avoid interpolating long NaN segments so we do not generate fake physiological values.

## Q6 What would you suggest for further improvement for real‑world deployment?
**Answer:**
1. Introduce IMU accelerometer and gyroscope data as motion reference. Mask / discard estimation windows under high‑motion conditions.
2. Add confidence metric for each window output; low‑confidence results should not be reported.
3. Tune hyper‑parameters of VMD / SSA with more diverse synthetic noisy datasets.
4. Combine multiple algorithms ensemble: cross‑validate HR result from FFT, VMD and harmonic‑suppression.

---

# Short written analysis (Task2, ≤1 page)
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
Leveraging prior engineering experience from PPG‑IMU wearable systems and referenced adaptive IMU motion‑artifact cancellation study, this practical hybrid signal‑processing pipeline is proposed for contact‑free mm‑wave radar vital‑sign estimation. It transfers knowledge from wearable devices to solve two dominant radar interferences: **respiratory‑harmonic leakage** and **body‑motion artifacts**.

1. **Adaptive IMU motion‑artifact screening & frequency‑domain cancellation**
When body‑worn IMU (accelerometer and gyroscope) sensor data is available:
- For each sliding analysis window, compute power spectra for radar phase‑displacement signal, tri‑axial accelerometer and tri‑axial gyroscope signals.
- Follow adaptive reference‑selection rules: compare dominant spectral peak frequencies, dynamically choose accelerometer, gyroscope, both sensors, or no IMU reference. This avoids the limitation of fixing one single IMU sensor as artifact reference.
- Perform frequency‑domain Wiener‑style spectral subtraction for motion‑artifact suppression **only under safe conditions**. Skip cancellation if motion‑artifact peak overlaps potential physiological HR frequency band, to prevent erasing genuine heartbeat components.
- If IMU hardware is absent, skip this cancellation step and fall back to pure radar‑signal processing.

2. **Radar‑domain signal processing branch for valid low‑motion windows**
After IMU‑based motion pre‑processing:
- Apply VMD variational‑mode decomposition for multi‑component signal separation.
- Execute respiratory‑harmonic notch suppression: estimate fundamental respiratory frequency and apply notch filters to its 2nd / 3rd /4th harmonics falling into HR band, to mitigate radar‑specific respiratory‑harmonic leakage.

3. **Sliding‑window post‑processing**
Apply segment‑wise median filter on time‑series HR outputs to reject abrupt HR outliers. Long NaN invalid segments will **not be interpolated**, to avoid generating fake physiological values.

4. **Wearable PPG as auxiliary cross‑validation reference (hybrid co‑existence scenario)**
If wearable PPG measurement is available:
- Use PPG‑derived HR as auxiliary reference.
- Mark radar output as low‑confidence when radar estimation deviates far from PPG reference.

5. **Confidence‑aware output**
Only report RR and HR under high overall confidence (low‑motion status, valid spectral peaks, cross‑validation pass if PPG is available). Suppress output instead of returning unreliable numbers.

> Transition note from PPG wearable to mm‑wave radar:
> IMU in wrist‑PPG captures wrist swinging movement; IMU for radar setup captures torso whole‑body motion. The adaptive frequency‑domain cancellation logic can be reused but physical signal sources differ. Respiratory‑harmonic interference is a unique pain‑point for radar phase‑displacement signal, which is generally not observed in wrist‑PPG systems, hence the dedicated harmonic‑suppression module.
