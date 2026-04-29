% =========================================================
% 02_prn_correlation.m
% Correlate IQ against GPS L1 C/A PRN codes
%
% This is the most important script. It tells you:
%   - whether GPS signal is actually present in the Lime capture
%   - the C/N0 estimate for each PRN
%   - whether the correlation peak is clean or buried in noise
%
% PRNs to test (from your current F9T ephemeris):
%   G03, G07, G08, G09, G16, G27
%
% A healthy GPS signal should show:
%   - a clear correlation peak 3-6 dB above the noise floor
%   - C/N0 estimate in the range 30-45 dB-Hz
%   - peak-to-noise ratio > 2.5 (this is your acquisition threshold)
%
% Usage:
%   Set IQ_FILE to your lime_iq_capture.dat path
%   Run the script
% =========================================================

clear; close all; clc;

%% --- Configuration ---
IQ_FILE      = 'lime_iq_capture.dat';
FS           = 2e6;          % sample rate Hz
F_L1         = 1575.42e6;   % GPS L1 center Hz
CODE_RATE    = 1.023e6;      % C/A code chip rate Hz
CODE_LEN     = 1023;         % chips per ms
N_COHERENT   = 1;            % coherent integration ms (keep at 1 for basic check)
DOPPLER_MAX  = 5000;         % Hz, search range
DOPPLER_STEP = 250;          % Hz, search step
PRNS_TO_TEST = [3 7 8 9 16 27];  % your ephemeris PRNs

%% --- Load IQ (first 5 seconds) ---
N_LOAD = min(5 * FS, 10e6);
fprintf('Loading %.0f samples from %s...\n', N_LOAD, IQ_FILE);
fid = fopen(IQ_FILE, 'rb');
if fid == -1, error('Cannot open: %s', IQ_FILE); end
raw = fread(fid, N_LOAD * 2, 'float32');
fclose(fid);
iq = raw(1:2:end) + 1j * raw(2:2:end);
fprintf('Loaded %d samples\n', length(iq));

%% --- Generate GPS L1 C/A PRN codes ---
function code = generate_prn(prn)
    % GPS L1 C/A gold code generator
    % G1 and G2 tap definitions per IS-GPS-200
    G2_taps = [
        [2,6]; [3,7]; [4,8]; [5,9]; [1,9]; [2,10]; [1,8]; [2,9];  % PRN 1-8
        [3,10]; [2,3]; [3,4]; [5,6]; [6,7]; [7,8]; [8,9]; [9,10]; % PRN 9-16
        [1,4]; [2,5]; [3,6]; [4,7]; [5,8]; [6,9]; [1,3]; [4,6];   % PRN 17-24
        [5,7]; [6,8]; [7,9]; [8,10]; [1,6]; [2,7]; [3,8]; [4,9];  % PRN 25-32
    ];
    g1 = ones(1,10);
    g2 = ones(1,10);
    code = zeros(1,1023);
    tap = G2_taps(prn, :);
    for i = 1:1023
        code(i) = xor(g1(10), xor(g2(tap(1)), g2(tap(2))));
        g1_new = xor(g1(3), g1(10));
        g2_new = xor(g2(2), xor(g2(3), xor(g2(6), xor(g2(8), xor(g2(9), g2(10))))));
        g1 = [g1_new g1(1:9)];
        g2 = [g2_new g2(1:9)];
    end
    code = 1 - 2*code; % convert to +1/-1
end

%% --- Upsample PRN to match sample rate ---
samples_per_chip = FS / CODE_RATE;
samples_per_ms   = round(FS * 1e-3);
chip_idx = floor((0:samples_per_ms-1) / samples_per_chip);
chip_idx = min(chip_idx, CODE_LEN-1);

%% --- Doppler bins ---
dopplers = -DOPPLER_MAX:DOPPLER_STEP:DOPPLER_MAX;
t = (0:samples_per_ms-1)' / FS;

%% --- Acquisition loop ---
fprintf('\n--- PRN Correlation Results ---\n');
fprintf('%-6s  %-10s  %-10s  %-10s  %-12s  %s\n', ...
    'PRN', 'Peak', 'Noise', 'Peak/Noise', 'C/N0 dB-Hz', 'Status');
fprintf('%s\n', repmat('-', 1, 65));

results = struct();
for pi = 1:length(PRNS_TO_TEST)
    prn = PRNS_TO_TEST(pi);
    
    % Generate and upsample PRN code
    code_chips = generate_prn(prn);
    code_upsampled = code_chips(chip_idx + 1);
    code_fft = conj(fft(code_upsampled));
    
    best_peak = 0;
    best_doppler = 0;
    best_delay = 0;
    all_peaks = zeros(length(dopplers), samples_per_ms);
    
    % Use first 20 ms of data
    n_blocks = min(20, floor(length(iq) / samples_per_ms));
    
    for di = 1:length(dopplers)
        doppler = dopplers(di);
        carrier = exp(-1j * 2 * pi * doppler * t);
        
        % Accumulate correlation over multiple ms
        acc = zeros(1, samples_per_ms);
        for bi = 1:n_blocks
            idx = (bi-1)*samples_per_ms + (1:samples_per_ms);
            block = iq(idx) .* carrier;
            block = block(:);
            cf = code_fft(:);
            corr = ifft(fft(block) .* cf);
            corr = corr(:).';
            acc = acc + abs(corr).^2;
        end
        acc = acc / n_blocks;
        all_peaks(di, :) = acc;
        
        [peak_val, peak_idx] = max(acc);
        if peak_val > best_peak
            best_peak = peak_val;
            best_doppler = doppler;
            best_delay = peak_idx;
        end
    end
    
    % Noise estimate: mean of all non-peak bins
    flat = all_peaks(:);
    flat_sorted = sort(flat);
    noise_est = mean(flat_sorted(1:round(0.9*end)));
    peak_to_noise = sqrt(best_peak / noise_est);
    
    % C/N0 estimate (Beaulieu method approximation)
    cn0_linear = (best_peak - noise_est) / (noise_est * 1e-3);
    cn0_db = 10*log10(max(cn0_linear, 1));
    
    results(pi).prn = prn;
    results(pi).peak = best_peak;
    results(pi).noise = noise_est;
    results(pi).ptn = peak_to_noise;
    results(pi).cn0 = cn0_db;
    results(pi).doppler = best_doppler;
    results(pi).delay = best_delay;
    results(pi).all_peaks = all_peaks;
    
    if peak_to_noise > 2.5
        status = 'FOUND';
    elseif peak_to_noise > 1.8
        status = 'WEAK';
    else
        status = 'NOT FOUND';
    end
    
    fprintf('G%02d    %-10.1f  %-10.1f  %-10.2f  %-12.1f  %s (Doppler: %+.0f Hz)\n', ...
        prn, best_peak, noise_est, peak_to_noise, cn0_db, status, best_doppler);
end

%% --- Plot correlation maps for each PRN ---
figure('Name', '02 - PRN Correlation Maps', 'Position', [100 100 1200 800]);
n_prns = length(PRNS_TO_TEST);
cols = 3;
rows = ceil(n_prns / cols);

for pi = 1:n_prns
    subplot(rows, cols, pi);
    imagesc(results(pi).all_peaks);
    colormap(jet);
    colorbar;
    xlabel('Code delay (samples)');
    ylabel('Doppler bin');
    title(sprintf('G%02d  P/N=%.2f  C/N0=%.1f dB-Hz', ...
        results(pi).prn, results(pi).ptn, results(pi).cn0));
    yticks(1:5:length(dopplers));
    yticklabels(dopplers(1:5:end)/1e3);
end
sgtitle('Acquisition Correlation Maps (Doppler kHz vs Code Delay)');

%% --- Summary plot: C/N0 by PRN ---
figure('Name', '02b - C/N0 Summary', 'Position', [100 550 700 350]);
cn0_vals = [results.cn0];
prn_labels = arrayfun(@(p) sprintf('G%02d', p), PRNS_TO_TEST, 'UniformOutput', false);
bar(cn0_vals);
xticklabels(prn_labels);
xlabel('PRN');
ylabel('C/N0 estimate (dB-Hz)');
title('Estimated C/N0 per PRN from raw IQ correlation');
yline(35, 'g--', 'Healthy tracking (35 dB-Hz)', 'LineWidth', 1.5);
yline(28, 'r--', 'Tracking threshold (~28 dB-Hz)', 'LineWidth', 1.5);
grid on;

fprintf('\n--- Interpretation ---\n');
fprintf('C/N0 > 35 dB-Hz : healthy, should track and reach bit sync\n');
fprintf('C/N0 28-35 dB-Hz: marginal, may track intermittently\n');
fprintf('C/N0 < 28 dB-Hz : too weak, will not reach bit sync\n');
fprintf('Peak/Noise > 2.5: signal found (matches GNSS-SDR threshold 2.6)\n');
