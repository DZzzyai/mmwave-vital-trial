# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 17:09:40 2026

@author: ZHANG
"""

# =========================================================
# Task 2 - Classical Denoising / Vital-Sign Extraction
# Dataset: mmWave FMCW radar (Resting vs Apnea)
# 方法: FFT / VMD / SSA / Harmonic-Suppressed FFT
# 含: 仿真测试, 工程化输出, 相对路径, __main__ 保护
# =========================================================

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')   # 无 GUI 环境也能保存图
import matplotlib.pyplot as plt
from scipy import signal
from scipy.signal import welch, find_peaks
from vmdpy import VMD

warnings.filterwarnings('ignore')


# ================= 配置区 =================
# ★ 从 code/ 往上找一级, 让 data/ 和 outputs/ 位于 Task2 根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
PROJECT_DIR = os.path.dirname(BASE_DIR) if os.path.basename(BASE_DIR) == 'code' else BASE_DIR
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
OUT_DIR = os.path.join(PROJECT_DIR, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

FS_RADAR = 333.3333
WINDOW_SEC = 10
STEP_SEC = 2
MEDFILT_KERNEL = 3

FILES = {
    'Resting': {
        'raw': os.path.join(DATA_DIR, 'Raw_1.xlsx'),
        'ground': os.path.join(DATA_DIR, 'Ground_1.xlsx')
    },
    'Apnea': {
        'raw': os.path.join(DATA_DIR, 'Raw_2.xlsx'),
        'ground': os.path.join(DATA_DIR, 'Ground_2.xlsx')
    }
}
# ==========================================


# ---------- 1. 数据加载 (加异常捕获) ----------
def load_and_align_data(raw_file, ground_file):
    try:
        df_raw = pd.read_excel(raw_file, sheet_name='VitalSig')
        time_radar = df_raw['Time_s'].values
        vital_sig = df_raw['VitalSig'].values

        df_gt = pd.read_excel(ground_file, sheet_name='HR_RR')
        time_gt = df_gt['Time_s'].values
        hr_gt = df_gt['HR_bpm'].values
        rr_gt = df_gt['RR_bpm'].values
    except FileNotFoundError as e:
        print(f"[ERROR] 文件不存在: {e}")
        return None, None, None, None
    except KeyError as e:
        print(f"[ERROR] Sheet 或列名错误: {e}")
        return None, None, None, None

    hr_gt_interp = np.interp(time_radar, time_gt, hr_gt)
    rr_gt_interp = np.interp(time_radar, time_gt, rr_gt)

    vital_sig = signal.detrend(vital_sig)
    return time_radar, vital_sig, hr_gt_interp, rr_gt_interp


# ---------- 2. 带通滤波 ----------
def butter_bandpass_filter(data, lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = max(lowcut / nyq, 1e-6)
    high = min(highcut / nyq, 0.999)
    b, a = signal.butter(order, [low, high], btype='band')
    return signal.filtfilt(b, a, data)


# ---------- 3. FFT 主频估计 (nperseg=4s, argmax) ----------
def estimate_fft(signal_data, fs, lowcut, highcut):
    if len(signal_data) < 4:
        return np.nan
    nperseg = min(len(signal_data), int(fs * 4))
    f, Pxx = welch(signal_data, fs, nperseg=nperseg)
    band = (f >= lowcut) & (f <= highcut)
    if np.sum(band) == 0 or np.all(np.isnan(Pxx[band])):
        return np.nan
    peak_freq = f[band][np.argmax(Pxx[band])]
    return peak_freq * 60


# ---------- 3b. FFT 主频估计 (高分辨率, find_peaks) ----------
def estimate_fft_high_res(signal_data, fs, lowcut, highcut, min_peak_ratio=0.3):
    """
    高分辨率 FFT 主频估计:
      1. Welch PSD (nperseg = 20 秒)
      2. find_peaks 找所有显著峰
      3. 排除边界伪峰, 选最强真实峰
    """
    if len(signal_data) < 4:
        return np.nan
    nperseg = min(len(signal_data), int(fs * 20))
    f, Pxx = welch(signal_data, fs, nperseg=nperseg)

    band = (f >= lowcut) & (f <= highcut)
    f_band = f[band]
    P_band = Pxx[band]
    if len(P_band) < 3:
        return np.nan

    peaks, _ = find_peaks(P_band, height=0)
    if len(peaks) == 0:
        return f_band[np.argmax(P_band)] * 60

    # 排除距边界 < 5% 带宽的伪峰
    band_width = highcut - lowcut
    margin = 0.05 * band_width
    valid = (f_band[peaks] >= lowcut + margin) & (f_band[peaks] <= highcut - margin)
    peaks = peaks[valid]
    if len(peaks) == 0:
        return f_band[np.argmax(P_band)] * 60

    heights = P_band[peaks]
    strong = heights >= min_peak_ratio * np.max(heights)
    peaks = peaks[strong]
    heights = heights[strong]
    return f_band[peaks[np.argmax(heights)]] * 60


# ---------- 4. VMD (暴露 alpha, 加模态能量权重) ----------
def estimate_vmd(signal_data, fs, K=6, alpha=2000):
    """VMD 分解, 按频带 + 能量权重挑选呼吸/心跳模态"""
    if len(signal_data) < 100:
        return np.nan, np.nan

    max_val = np.max(np.abs(signal_data))
    if max_val < 1e-10:
        return np.nan, np.nan
    signal_norm = signal_data / max_val

    try:
        u, u_hat, omega = VMD(signal_norm, alpha, 0.1, K, 0, 1, 1e-7)
        center_freqs = omega[-1] * fs
    except Exception:
        return np.nan, np.nan

    valid = np.isfinite(center_freqs)
    center_freqs = center_freqs[valid]
    if len(center_freqs) == 0:
        return np.nan, np.nan

    energies = np.sum(np.abs(u) ** 2, axis=1)
    energies = energies[valid]
    energies_norm = energies / (np.sum(energies) + 1e-12)

    resp_idx = np.where((center_freqs >= 0.1) & (center_freqs <= 0.5) & (energies_norm > 0.05))[0]
    heart_idx = np.where((center_freqs >= 0.8) & (center_freqs <= 2.0) & (energies_norm > 0.05))[0]

    resp_hz = center_freqs[resp_idx][np.argmax(energies_norm[resp_idx])] if len(resp_idx) > 0 else np.nan
    if len(heart_idx) > 0:
        best_heart = heart_idx[np.argmax(energies_norm[heart_idx])]
        heart_hz = center_freqs[best_heart]
    else:
        heart_hz = np.nan

    resp_bpm = resp_hz * 60 if not np.isnan(resp_hz) else np.nan
    heart_bpm = heart_hz * 60 if not np.isnan(heart_hz) else np.nan
    return resp_bpm, heart_bpm


# ---------- 5. SSA (修正对角平均 + 自适应分量) ----------
def ssa_decompose(signal_in, window_length=100, n_components=5):
    N = len(signal_in)
    if N < window_length:
        return signal_in

    L = window_length
    K = N - L + 1

    X = np.zeros((L, K))
    for i in range(K):
        X[:, i] = signal_in[i:i + L]

    U, s, Vt = np.linalg.svd(X, full_matrices=False)

    # 自适应选择有效分量 (累积能量 95%, 至少 2 个)
    energy = s ** 2
    cum_energy = np.cumsum(energy) / np.sum(energy)
    n_eff = max(2, np.searchsorted(cum_energy, 0.95) + 1)
    n_eff = min(n_eff, n_components, len(s))

    X_recon = U[:, :n_eff] @ np.diag(s[:n_eff]) @ Vt[:n_eff, :]

    # 正确对角平均
    recon = np.zeros(N)
    counts = np.zeros(N)
    for i in range(L):
        for j in range(K):
            recon[i + j] += X_recon[i, j]
            counts[i + j] += 1
    recon = recon / np.maximum(counts, 1)

    return recon


# ---------- 6. 谐波抑制 (加 padding 防边缘效应) ----------
def estimate_hr_harmonic_suppressed(signal_data, fs, pad_sec=1.0):
    """
    谐波抑制 FFT:
      1. 呼吸带 0.15-0.5 Hz 估计 f_resp (排除 DC 边缘)
      2. 对 2/3/4 次谐波做陷波
      3. 心跳带 FFT
    """
    if len(signal_data) < fs * 2:
        return np.nan

    # ★ 呼吸带 0.15 起
    resp_seg = butter_bandpass_filter(signal_data, 0.15, 0.5, fs)
    nperseg = min(len(resp_seg), int(fs * 4))
    f, Pxx = welch(resp_seg, fs, nperseg=nperseg)
    band = (f >= 0.15) & (f <= 0.5)
    if np.sum(band) == 0:
        return np.nan
    f_resp = f[band][np.argmax(Pxx[band])]

    pad_n = int(pad_sec * fs)
    padded = np.concatenate([signal_data[:pad_n][::-1],
                             signal_data,
                             signal_data[-pad_n:][::-1]])
    nyq = fs / 2
    for n in [2, 3, 4]:
        f_harm = n * f_resp
        if 0.8 <= f_harm <= 2.0 and f_harm < nyq * 0.95:
            b, a = signal.iirnotch(f_harm, 30, fs)
            padded = signal.filtfilt(b, a, padded)

    filtered = padded[pad_n:-pad_n]
    heart_seg = butter_bandpass_filter(filtered, 0.8, 2.0, fs)
    return estimate_fft(heart_seg, fs, 0.8, 2.0)


# ---------- 7. 滑动窗口 ----------
def sliding_window_estimate(vital_sig, fs, window_sec, step_sec, method='fft'):
    win_size = int(window_sec * fs)
    step_size = int(step_sec * fs)
    t_list, rr_list, hr_list = [], [], []

    for start in range(0, len(vital_sig) - win_size, step_size):
        seg = vital_sig[start:start + win_size]
        t_center = (start + win_size / 2) / fs

        # 窗口质量预检查
        if np.any(~np.isfinite(seg)):
            t_list.append(t_center); rr_list.append(np.nan); hr_list.append(np.nan)
            continue
        if np.std(seg) < 1e-8:
            t_list.append(t_center); rr_list.append(np.nan); hr_list.append(np.nan)
            continue

        resp_seg = butter_bandpass_filter(seg, 0.1, 0.5, fs)
        heart_seg = butter_bandpass_filter(seg, 0.8, 2.0, fs)

        if method == 'fft':
            rr = estimate_fft(resp_seg, fs, 0.1, 0.5)
            hr = estimate_fft(heart_seg, fs, 0.8, 2.0)
        elif method == 'vmd':
            rr, hr = estimate_vmd(seg, fs, K=6, alpha=2000)
        elif method == 'ssa':
            seg_ssa = ssa_decompose(seg, window_length=min(200, len(seg) // 2))
            rr = estimate_fft(butter_bandpass_filter(seg_ssa, 0.1, 0.5, fs), fs, 0.1, 0.5)
            hr = estimate_fft(butter_bandpass_filter(seg_ssa, 0.8, 2.0, fs), fs, 0.8, 2.0)
        elif method == 'harmonic':
            rr = estimate_fft(resp_seg, fs, 0.1, 0.5)
            hr = estimate_hr_harmonic_suppressed(seg, fs)
        else:
            rr, hr = np.nan, np.nan

        t_list.append(t_center)
        rr_list.append(rr)
        hr_list.append(hr)

    return np.array(t_list), np.array(rr_list), np.array(hr_list)


# ---------- 8. 中值滤波 (修正 NaN 处理) ----------
def median_filter_series(series, kernel=3):
    series = np.asarray(series, dtype=float)
    out = series.copy()
    valid = np.isfinite(series)
    if np.sum(valid) < kernel:
        return out

    idx = np.where(valid)[0]
    breaks = np.where(np.diff(idx) > 1)[0]
    segments = np.split(idx, breaks + 1)

    for seg in segments:
        if len(seg) >= kernel:
            out[seg] = signal.medfilt(series[seg], kernel_size=kernel)
    return out


# ---------- 9. 误差指标 ----------
def compute_metrics(est, gt):
    mask = np.isfinite(est) & np.isfinite(gt)
    if np.sum(mask) < 2:
        return dict(mae=np.nan, rmse=np.nan, mape=np.nan, hit2=np.nan, corr=np.nan, n=int(np.sum(mask)))
    est_v, gt_v = est[mask], gt[mask]
    mae = np.mean(np.abs(est_v - gt_v))
    rmse = np.sqrt(np.mean((est_v - gt_v) ** 2))
    valid_mape = np.abs(gt_v) > 5
    mape = np.mean(np.abs(est_v[valid_mape] - gt_v[valid_mape]) / np.abs(gt_v[valid_mape])) * 100 \
        if np.sum(valid_mape) > 0 else np.nan
    hit = np.mean(np.abs(est_v - gt_v) <= 2.0) * 100
    corr = np.nan if (np.std(est_v) < 1e-6 or np.std(gt_v) < 1e-6) else np.corrcoef(est_v, gt_v)[0, 1]
    return dict(mae=mae, rmse=rmse, mape=mape, hit2=hit, corr=corr, n=int(np.sum(mask)))


# ---------- 10. 仿真信号 ----------
def simulate_radar_signal(fs=100, duration=60, rr_bpm=15, hr_bpm=72,
                          rr_harmonic_ratio=0.3, noise_sigma=0.05):
    """
    仿真 mmWave 雷达相位信号:
      呼吸 (基频 + 2/3 次谐波) + 心跳 + 噪声
    ★ 不做任何滤波, 保持理想正弦叠加, 防止滤波边缘伪峰
    """
    t = np.arange(0, duration, 1 / fs)
    f_rr = rr_bpm / 60.0
    f_hr = hr_bpm / 60.0

    resp = 3.0 * np.sin(2 * np.pi * f_rr * t)
    resp += rr_harmonic_ratio * np.sin(2 * np.pi * 2 * f_rr * t)
    resp += rr_harmonic_ratio * 0.5 * np.sin(2 * np.pi * 3 * f_rr * t)

    heart = 0.1 * np.sin(2 * np.pi * f_hr * t)
    noise = noise_sigma * np.random.randn(len(t))

    return t, resp + heart + noise, rr_bpm, hr_bpm


# ---------- 11. 仿真测试 ----------
def run_simulation_test():
    """仿真测试: 谐波落在心跳带内, 演示抑制前后的差异"""
    print("\n" + "=" * 60)
    print(">>> 仿真测试: 呼吸谐波干扰心跳")
    print("=" * 60)

    # ★ 呼吸带下限 0.20 Hz (12 BPM), 彻底避开 0.15 Hz 边缘伪峰
    RESP_LOW, RESP_HIGH = 0.20, 0.5
    HEART_LOW, HEART_HIGH = 0.8, 2.0

    scenarios = [
        {'name': 'Scenario A: 4th harmonic ',
         'rr_bpm': 18, 'hr_bpm': 60},
        {'name': 'Scenario B: 4th harmonic ',
         'rr_bpm': 18, 'hr_bpm': 70},
    ]

    all_results = []
    for sc in scenarios:
        print(f"\n--- {sc['name']} ---")

        t, sig, rr_true, hr_true = simulate_radar_signal(
            fs=100, duration=60,
            rr_bpm=sc['rr_bpm'], hr_bpm=sc['hr_bpm'],
            rr_harmonic_ratio=0.3, noise_sigma=0.03
        )

        # ★ 一次滤波到位, 呼吸带 0.20-0.5, 心跳带 0.8-2.0
        resp_seg = butter_bandpass_filter(sig, RESP_LOW, RESP_HIGH, 100)
        heart_seg = butter_bandpass_filter(sig, HEART_LOW, HEART_HIGH, 100)

        rr_fft = estimate_fft_high_res(resp_seg, 100, RESP_LOW, RESP_HIGH)
        hr_fft = estimate_fft_high_res(heart_seg, 100, HEART_LOW, HEART_HIGH)

        hr_harm = estimate_hr_harmonic_suppressed(sig, 100)

        print(f"    真实 RR = {rr_true} BPM, 真实 HR = {hr_true} BPM")
        print(f"    4th harmonic = {rr_true * 4} BPM")
        print(f"    [FFT]      RR = {rr_fft:.2f}, HR = {hr_fft:.2f}  (误差 {hr_fft - hr_true:+.2f})")
        print(f"    [Harmonic] RR = {rr_fft:.2f}, HR = {hr_harm:.2f}  (误差 {hr_harm - hr_true:+.2f})")

        all_results.append({
            'scenario': sc['name'],
            'RR_true': rr_true, 'HR_true': hr_true,
            'RR_fft': rr_fft, 'HR_fft': hr_fft,
            'HR_harm': hr_harm,
            'HR_fft_err': hr_fft - hr_true,
            'HR_harm_err': hr_harm - hr_true
        })

    sim_df = pd.DataFrame(all_results)
    sim_df.to_csv(os.path.join(OUT_DIR, 'simulation_result.csv'), index=False)
    print(f"\n仿真结果已保存: {os.path.join(OUT_DIR, 'simulation_result.csv')}")


# ================= 主流程 =================
def main():
    # ---------- 仿真测试 ----------
    run_simulation_test()

    # ---------- 真实数据 ----------
    results = {}
    metrics_rows = []

    for condition, files in FILES.items():
        print(f"\n{'=' * 60}")
        print(f">>> 处理 {condition} 数据...")
        print('=' * 60)

        t_radar, vitalsig, hr_gt, rr_gt = load_and_align_data(files['raw'], files['ground'])
        if vitalsig is None:
            print(f"[SKIP] {condition} 数据加载失败")
            continue

        print(f"数据长度: {len(vitalsig)} 采样点, 时长: {len(vitalsig) / FS_RADAR:.1f} 秒")

        t_fft, rr_fft, hr_fft = sliding_window_estimate(vitalsig, FS_RADAR, WINDOW_SEC, STEP_SEC, 'fft')
        t_vmd, rr_vmd, hr_vmd = sliding_window_estimate(vitalsig, FS_RADAR, WINDOW_SEC, STEP_SEC, 'vmd')
        t_ssa, rr_ssa, hr_ssa = sliding_window_estimate(vitalsig, FS_RADAR, WINDOW_SEC, STEP_SEC, 'ssa')
        t_har, rr_har, hr_har = sliding_window_estimate(vitalsig, FS_RADAR, WINDOW_SEC, STEP_SEC, 'harmonic')

        hr_fft_med = median_filter_series(hr_fft, MEDFILT_KERNEL)
        hr_vmd_med = median_filter_series(hr_vmd, MEDFILT_KERNEL)
        hr_ssa_med = median_filter_series(hr_ssa, MEDFILT_KERNEL)
        hr_har_med = median_filter_series(hr_har, MEDFILT_KERNEL)

        rr_gt_at_t = np.interp(t_fft, t_radar, rr_gt)
        hr_gt_at_t = np.interp(t_fft, t_radar, hr_gt)

        for name, rr_e, hr_e in [
            ('FFT',      rr_fft, hr_fft_med),
            ('VMD',      rr_vmd, hr_vmd_med),
            ('SSA',      rr_ssa, hr_ssa_med),
            ('Harmonic', rr_har, hr_har_med),
        ]:
            m_rr = compute_metrics(rr_e, rr_gt_at_t)
            m_hr = compute_metrics(hr_e, hr_gt_at_t)
            metrics_rows.append({
                'condition': condition, 'method': name,
                'RR_MAE': m_rr['mae'], 'RR_RMSE': m_rr['rmse'], 'RR_MAPE': m_rr['mape'],
                'RR_hit2': m_rr['hit2'], 'RR_corr': m_rr['corr'],
                'HR_MAE': m_hr['mae'], 'HR_RMSE': m_hr['rmse'], 'HR_MAPE': m_hr['mape'],
                'HR_hit2': m_hr['hit2'], 'HR_corr': m_hr['corr'],
            })

        win_df = pd.DataFrame({
            't': t_fft, 'rr_gt': rr_gt_at_t, 'hr_gt': hr_gt_at_t,
            'rr_fft': rr_fft, 'hr_fft': hr_fft, 'hr_fft_med': hr_fft_med,
            'rr_vmd': rr_vmd, 'hr_vmd': hr_vmd, 'hr_vmd_med': hr_vmd_med,
            'rr_ssa': rr_ssa, 'hr_ssa': hr_ssa, 'hr_ssa_med': hr_ssa_med,
            'rr_har': rr_har, 'hr_har': hr_har, 'hr_har_med': hr_har_med,
        })
        win_df.to_csv(os.path.join(OUT_DIR, f'window_estimates_{condition}.csv'), index=False)

        results[condition] = {
            't_radar': t_radar, 'vitalsig': vitalsig,
            't_fft': t_fft, 'rr_fft': rr_fft, 'hr_fft': hr_fft, 'hr_fft_med': hr_fft_med,
            't_vmd': t_vmd, 'rr_vmd': rr_vmd, 'hr_vmd': hr_vmd, 'hr_vmd_med': hr_vmd_med,
            't_ssa': t_ssa, 'rr_ssa': rr_ssa, 'hr_ssa': hr_ssa, 'hr_ssa_med': hr_ssa_med,
            't_har': t_har, 'rr_har': rr_har, 'hr_har': hr_har, 'hr_har_med': hr_har_med,
            'rr_gt_at_t': rr_gt_at_t, 'hr_gt_at_t': hr_gt_at_t
        }

    metrics_df = pd.DataFrame(metrics_rows)
    metrics_df.to_csv(os.path.join(OUT_DIR, 'metrics_result.csv'), index=False)
    print("\n指标表已保存:", os.path.join(OUT_DIR, 'metrics_result.csv'))
    print(metrics_df.to_string(index=False))

    # 可视化
    if len(results) > 0:
        for condition, r in results.items():
            fig, axes = plt.subplots(3, 1, figsize=(12, 10))
            axes[0].plot(r['t_fft'], r['hr_gt_at_t'], 'k-', linewidth=2.5, label='Ground Truth')
            axes[0].plot(r['t_fft'], r['hr_fft_med'], 'o-', alpha=0.7, label='FFT (median)')
            axes[0].plot(r['t_vmd'], r['hr_vmd_med'], 's-', alpha=0.7, label='VMD (median)')
            axes[0].plot(r['t_ssa'], r['hr_ssa_med'], '^-', alpha=0.7, label='SSA (median)')
            axes[0].plot(r['t_har'], r['hr_har_med'], 'd-', alpha=0.9, label='Harmonic (median)')
            axes[0].set_title(f'HR - {condition}'); axes[0].legend(); axes[0].grid(True)

            axes[1].plot(r['t_fft'], r['rr_gt_at_t'], 'k-', linewidth=2.5, label='Ground Truth')
            axes[1].plot(r['t_fft'], r['rr_fft'], 'o-', alpha=0.6, label='FFT')
            axes[1].plot(r['t_vmd'], r['rr_vmd'], 's-', alpha=0.6, label='VMD')
            axes[1].set_title(f'RR - {condition}'); axes[1].legend(); axes[1].grid(True)

            f, Pxx = welch(r['vitalsig'], FS_RADAR,
                           nperseg=min(len(r['vitalsig']), int(FS_RADAR * 10)))
            axes[2].semilogy(f, Pxx)
            axes[2].set_xlim(0, 3)
            axes[2].axvspan(0.1, 0.5, color='g', alpha=0.3, label='Resp Band')
            axes[2].axvspan(0.8, 2.0, color='r', alpha=0.3, label='Heart Band')
            axes[2].set_title(f'PSD - {condition}'); axes[2].legend(); axes[2].grid(True)

            plt.tight_layout()
            plt.savefig(os.path.join(OUT_DIR, f'task2_{condition}.png'), dpi=150, bbox_inches='tight')
            plt.close()

            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(r['t_fft'], r['hr_gt_at_t'] - r['hr_fft_med'], 'o-', alpha=0.6, label='FFT error')
            ax.plot(r['t_har'], r['hr_gt_at_t'] - r['hr_har_med'], 'd-', alpha=0.9, label='Harmonic error')
            ax.axhline(0, color='k', linestyle='--')
            ax.set_title(f'HR Error over Time - {condition}')
            ax.set_xlabel('Time (s)'); ax.set_ylabel('HR error (BPM)')
            ax.legend(); ax.grid(True)
            plt.tight_layout()
            plt.savefig(os.path.join(OUT_DIR, f'task2_error_{condition}.png'), dpi=150, bbox_inches='tight')
            plt.close()


if __name__ == '__main__':
    main()