% =========================================================
% 04_rtl_vs_lime.m
% Compare RTL and Lime IQ captures side by side
%
% This directly answers: why does the RTL work and the Lime not?
%
% It compares:
%   - noise floor
%   - DC spike magnitude
%   - correlation peak sharpness
%   - C/N0 estimate for the same PRN
%
% Usage:
%   You need a .dat capture from the RTL too.
%   To capture RTL IQ, use the same approach as the Lime
%   but with the RTL signal source config.
%   Set LIME_FILE and RTL_FILE paths below.
% =========================================================

clear; close all; clc;

%% --- Configuration ---
LIME_FILE   = 'lime_iq_capture.dat';
RTL_FILE    = 'rtl_iq_capture.dat';    % capture this separately
FS_LIME     = 2e6;
FS_RTL      = 2e6;                     % adjust if RTL was captured at different rate
PRN         = 27;                      % use the same PRN for fair comparison
DOPPLER_HZ  = 0;                       % update from 02_prn_correlation results
N_LOAD      = 2e6;                     % 1 second each

CODE_RATE   = 1.023e6;
CODE_LEN    = 1023;

%% --- PRN generator ---
function code = generate_prn(prn)
    G2_taps = [
        [2,6]; [3,7]; [4,8]; [5,9]; [1,9]; [2,10]; [1,8]; [2,9];
        [3,10]; [2,3]; [3,4]; [5,6]; [6,7]; [7,8]; [8,9]; [9,10];
        [1,4]; [2,5]; [3,6]; [4,7]; [5,8]; [6,9]; [1,3]; [4,6];
        [5,7]; [6,8]; [7,9]; [8,10]; [1,6]; [2,7]; [3,8]; [4,9];
    ];
    g1 = ones(1,10); g2 = ones(1,10);
    code = zeros(1,1023);
    tap = G2_taps(prn,:);
    for i = 1:1023
        code(i) = xor(g1(10), xor(g2(tap(1)), g2(tap(2))));
        g1_new = xor(g1(3), g1(10));
        g2_new = xor(g2(2), xor(g2(3), xor(g2(6), xor(g2(8), xor(g2(9), g2(10))))));
        g1 = [g1_new g1(1:9)]; g2 = [g2_new g2(1:9)];
    end
    code = 1 - 2*code;
end

%% --- Load function ---
function iq = load_iq(fname, n)
    fid = fopen(fname, 'rb');
    if fid == -1, error('Cannot open: %s', fname); end
    raw = fread(fid, n*2, 'float32');
    fclose(fid);
    iq = raw(1:2:end) + 1j*raw(2:2:end);
end

%% --- Correlation function ---
function [peak_ptn, cn0, corr_vec] = run_correlation(iq, fs, prn, doppler)
    code_rate = 1.023e6;
    code_len  = 1023;
    spm = round(fs * 1e-3);
    spc = fs / code_rate;
    chip_idx = min(floor((0:spm-1) / spc), code_len-1);
    
    code_chips = generate_prn(prn);
    code_up = code_chips(chip_idx+1);
    code_fft = conj(fft(code_up));
    
    t = (0:spm-1)' / fs;
    carrier = exp(-1j * 2*pi*doppler*t);
    
    n_blocks = min(20, floor(length(iq)/spm));
    acc = zeros(1, spm);
    for b = 1:n_blocks
        idx = (b-1)*spm + (1:spm);
        block = iq(idx) .* carrier;
        corr = ifft(fft(block) .* code_fft);
        acc = acc + abs(corr).^2;
    end
    acc = acc / n_blocks;
    corr_vec = acc;
    
    [peak_val, ~] = max(acc);
    flat = sort(acc);
    noise_est = mean(flat(1:round(0.9*end)));
    peak_ptn = sqrt(peak_val / noise_est);
    cn0_lin = (peak_val - noise_est) / (noise_est * 1e-3);
    cn0 = 10*log10(max(cn0_lin, 1));
end

%% --- Check RTL file exists ---
rtl_available = exist(RTL_FILE, 'file');
if ~rtl_available
    fprintf('NOTE: RTL capture file not found: %s\n', RTL_FILE);
    fprintf('      Running Lime analysis only.\n');
    fprintf('      To capture RTL IQ, see instructions at bottom of this script.\n\n');
end

%% --- Load and analyze Lime ---
fprintf('Analyzing Lime IQ...\n');
iq_lime = load_iq(LIME_FILE, N_LOAD);
[lime_ptn, lime_cn0, lime_corr] = run_correlation(iq_lime, FS_LIME, PRN, DOPPLER_HZ);

N_SPEC = 2^18;
[pxx_lime, f_lime] = pwelch(iq_lime, hanning(N_SPEC), N_SPEC/2, N_SPEC, FS_LIME, 'centered');
noise_lime = median(10*log10(pxx_lime));
dc_lime = 10*log10(pxx_lime(find(abs(f_lime)==min(abs(f_lime)),1)));

fprintf('Lime — PRN G%02d: Peak/Noise=%.2f  C/N0=%.1f dB-Hz\n', PRN, lime_ptn, lime_cn0);
fprintf('Lime — Noise floor: %.1f dB  DC spike: %.1f dB (%.1f dB above floor)\n', ...
    noise_lime, dc_lime, dc_lime - noise_lime);

%% --- Load and analyze RTL if available ---
if rtl_available
    fprintf('Analyzing RTL IQ...\n');
    iq_rtl = load_iq(RTL_FILE, N_LOAD);
    [rtl_ptn, rtl_cn0, rtl_corr] = run_correlation(iq_rtl, FS_RTL, PRN, DOPPLER_HZ);
    
    [pxx_rtl, f_rtl] = pwelch(iq_rtl, hanning(N_SPEC), N_SPEC/2, N_SPEC, FS_RTL, 'centered');
    noise_rtl = median(10*log10(pxx_rtl));
    dc_rtl = 10*log10(pxx_rtl(find(abs(f_rtl)==min(abs(f_rtl)),1)));
    
    fprintf('RTL  — PRN G%02d: Peak/Noise=%.2f  C/N0=%.1f dB-Hz\n', PRN, rtl_ptn, rtl_cn0);
    fprintf('RTL  — Noise floor: %.1f dB  DC spike: %.1f dB (%.1f dB above floor)\n', ...
        noise_rtl, dc_rtl, dc_rtl - noise_rtl);
end

%% --- Plots ---
figure('Name', '04 - RTL vs Lime Comparison', 'Position', [100 100 1200 800]);

% Spectrum comparison
if rtl_available
    subplot(2,2,1);
    plot(f_lime/1e6, 10*log10(pxx_lime), 'b'); hold on;
    plot(f_rtl/1e6,  10*log10(pxx_rtl),  'r');
    legend('Lime','RTL'); grid on;
    xlabel('Freq offset (MHz)'); ylabel('dB');
    title('Power Spectrum — Lime (blue) vs RTL (red)');
    xlim([-1 1]);
    
    subplot(2,2,2);
    mask_lime = abs(f_lime) < 100e3;
    mask_rtl  = abs(f_rtl)  < 100e3;
    plot(f_lime(mask_lime)/1e3, 10*log10(pxx_lime(mask_lime)), 'b'); hold on;
    plot(f_rtl(mask_rtl)/1e3,  10*log10(pxx_rtl(mask_rtl)),  'r');
    legend('Lime','RTL'); grid on;
    xlabel('Freq offset (kHz)'); ylabel('dB');
    title('DC Spike Detail ±100 kHz');
    xline(0,'k--');
    
    subplot(2,2,3);
    plot(lime_corr/max(lime_corr), 'b'); hold on;
    plot(rtl_corr/max(rtl_corr), 'r');
    legend('Lime','RTL'); grid on;
    xlabel('Code delay (samples)'); ylabel('Normalized correlation');
    title(sprintf('PRN G%02d Correlation Peak — Lime vs RTL', PRN));
    
    subplot(2,2,4);
    bar([lime_cn0 rtl_cn0]);
    xticklabels({'Lime','RTL'});
    ylabel('C/N0 (dB-Hz)'); grid on;
    yline(35,'g--','Healthy'); yline(28,'r--','Threshold');
    title(sprintf('C/N0 Comparison — PRN G%02d', PRN));
    
else
    % Lime only
    subplot(2,1,1);
    plot(f_lime/1e6, 10*log10(pxx_lime), 'b'); grid on;
    xlabel('Freq offset (MHz)'); ylabel('dB');
    title('Lime Power Spectrum');
    xlim([-1 1]);
    xline(0,'r--','DC');
    
    subplot(2,1,2);
    plot(lime_corr/max(lime_corr), 'b'); grid on;
    xlabel('Code delay (samples)'); ylabel('Normalized correlation');
    title(sprintf('PRN G%02d Correlation (Lime only — capture RTL to compare)', PRN));
end

sgtitle('RTL vs Lime IQ Analysis');

%% --- Comparison summary ---
fprintf('\n--- Comparison Summary ---\n');
if rtl_available
    fprintf('%-20s  %-10s  %-10s  %-12s\n', 'Metric', 'Lime', 'RTL', 'Gap');
    fprintf('%-20s  %-10.1f  %-10.1f  %-12.1f\n', 'C/N0 (dB-Hz)', lime_cn0, rtl_cn0, rtl_cn0-lime_cn0);
    fprintf('%-20s  %-10.2f  %-10.2f  %-12.2f\n', 'Peak/Noise ratio', lime_ptn, rtl_ptn, rtl_ptn-lime_ptn);
    fprintf('%-20s  %-10.1f  %-10.1f  %-12.1f\n', 'DC above floor (dB)', dc_lime-noise_lime, dc_rtl-noise_rtl, (dc_lime-noise_lime)-(dc_rtl-noise_rtl));
    
    if rtl_cn0 - lime_cn0 > 5
        fprintf('\nCONCLUSION: Lime C/N0 is >5 dB below RTL.\n');
        fprintf('            Hardware bandpass filter is the recommended fix.\n');
    elseif rtl_cn0 - lime_cn0 > 2
        fprintf('\nCONCLUSION: Lime C/N0 is marginally below RTL.\n');
        fprintf('            Signal is borderline — hardware filter may help.\n');
    else
        fprintf('\nCONCLUSION: Lime and RTL C/N0 are comparable.\n');
        fprintf('            The problem is not signal level — investigate elsewhere.\n');
    end
else
    fprintf('Lime C/N0: %.1f dB-Hz\n', lime_cn0);
    fprintf('Run with RTL capture for full comparison.\n');
    fprintf('\nTo capture RTL IQ on hft02:\n');
    fprintf('  Use rtl_sdr -f 1575420000 -s 2000000 -n 20000000 rtl_iq_capture.bin\n');
    fprintf('  Then convert: rtl_sdr output is uint8, needs offset/scale to float32\n');
    fprintf('  Or configure GNSS-SDR with RTL source and dump=true\n');
end
