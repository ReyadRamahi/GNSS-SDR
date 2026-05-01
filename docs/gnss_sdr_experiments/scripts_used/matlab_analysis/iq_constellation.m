% =========================================================
% 05_iq_constellation.m
% IQ scatter plot / constellation diagram of raw Lime capture
%
% This tells you:
%   - whether the IQ samples are balanced (I and Q equal power)
%   - how severe the DC offset is (cluster center away from origin)
%   - whether there is IQ imbalance (elliptical vs circular cloud)
%   - the noise radius relative to signal power
%   - whether any structure is visible (GPS is spread spectrum so
%     a healthy capture should look like a circular Gaussian cloud
%     centered at the origin)
%
% Usage:
%   Set IQ_FILE to your lime_iq_capture.dat path
%   Run the script
% =========================================================

clear; close all; clc;

%% --- Configuration ---
IQ_FILE     = 'lime_iq_capture.dat';
FS          = 2e6;          % sample rate Hz
N_PLOT      = 50000;        % samples to plot in scatter (keep low for speed)
N_LOAD      = 500000;       % samples to load for statistics (0.25 seconds)

%% --- Load IQ ---
fprintf('Loading %d samples from %s...\n', N_LOAD, IQ_FILE);
fid = fopen(IQ_FILE, 'rb');
if fid == -1, error('Cannot open: %s', IQ_FILE); end
raw = fread(fid, N_LOAD * 2, 'float32');
fclose(fid);

I = raw(1:2:end);
Q = raw(2:2:end);
fprintf('Loaded %d samples\n', length(I));

%% --- Statistics ---
I_mean  = mean(I);
Q_mean  = mean(Q);
I_std   = std(I);
Q_std   = std(Q);
I_power = mean(I.^2);
Q_power = mean(Q.^2);
total_power = I_power + Q_power;

dc_offset   = sqrt(I_mean^2 + Q_mean^2);
iq_imbalance = abs(I_std - Q_std) / mean([I_std Q_std]) * 100;

fprintf('\n--- IQ Statistics ---\n');
fprintf('I mean (DC):      %+.6f\n', I_mean);
fprintf('Q mean (DC):      %+.6f\n', Q_mean);
fprintf('DC offset mag:    %.6f\n', dc_offset);
fprintf('I std dev:        %.6f\n', I_std);
fprintf('Q std dev:        %.6f\n', Q_std);
fprintf('IQ imbalance:     %.2f%%\n', iq_imbalance);
fprintf('I power:          %.6f\n', I_power);
fprintf('Q power:          %.6f\n', Q_power);
fprintf('Total power:      %.6f\n', total_power);
fprintf('Power ratio I/Q:  %.3f dB\n', 10*log10(I_power/Q_power));

if iq_imbalance > 5
    fprintf('WARNING: IQ imbalance >5%% — amplitude mismatch between I and Q paths\n');
else
    fprintf('OK: IQ imbalance <5%%\n');
end

if dc_offset > 0.1 * mean([I_std Q_std])
    fprintf('WARNING: DC offset is >10%% of noise std — significant DC bias\n');
else
    fprintf('OK: DC offset is small relative to noise\n');
end

%% --- Subsample for scatter plot ---
idx = round(linspace(1, length(I), min(N_PLOT, length(I))));
I_plot = I(idx);
Q_plot = Q(idx);

%% --- Plot 1: Scatter constellation ---
figure('Name', '05 - IQ Constellation', 'Position', [100 100 700 700]);

% Density scatter using histogram2
subplot(1,1,1);
h = histogram2(I_plot, Q_plot, 200, 'DisplayStyle', 'tile', 'ShowEmptyBins', 'off');
colormap(jet);
colorbar;
axis equal;
xlabel('I (In-phase)');
ylabel('Q (Quadrature)');
title(sprintf('IQ Constellation — %dk samples\nDC offset: I=%.4f Q=%.4f  IQ imbalance: %.1f%%', ...
    round(N_PLOT/1000), I_mean, Q_mean, iq_imbalance));
grid on;

% Mark origin
hold on;
plot(0, 0, 'w+', 'MarkerSize', 12, 'LineWidth', 2);
% Mark DC center
plot(I_mean, Q_mean, 'rx', 'MarkerSize', 12, 'LineWidth', 2);
legend('','Origin (0,0)', 'DC center', 'Location', 'northeast');

%% --- Plot 2: I and Q histograms ---
figure('Name', '05b - IQ Histograms', 'Position', [850 100 700 500]);

subplot(2,1,1);
histogram(I_plot, 200, 'FaceColor', 'b', 'EdgeColor', 'none', 'Normalization', 'pdf');
hold on;
x = linspace(min(I_plot), max(I_plot), 500);
plot(x, normpdf(x, I_mean, I_std), 'r-', 'LineWidth', 2);
xline(0, 'k--', 'Zero', 'LineWidth', 1);
xline(I_mean, 'r--', sprintf('DC=%.4f', I_mean), 'LineWidth', 1);
xlabel('Amplitude'); ylabel('PDF');
title(sprintf('I channel — mean=%.4f  std=%.4f', I_mean, I_std));
grid on;

subplot(2,1,2);
histogram(Q_plot, 200, 'FaceColor', 'r', 'EdgeColor', 'none', 'Normalization', 'pdf');
hold on;
x = linspace(min(Q_plot), max(Q_plot), 500);
plot(x, normpdf(x, Q_mean, Q_std), 'b-', 'LineWidth', 2);
xline(0, 'k--', 'Zero', 'LineWidth', 1);
xline(Q_mean, 'b--', sprintf('DC=%.4f', Q_mean), 'LineWidth', 1);
xlabel('Amplitude'); ylabel('PDF');
title(sprintf('Q channel — mean=%.4f  std=%.4f', Q_mean, Q_std));
grid on;

sgtitle('IQ Channel Distributions');

%% --- Plot 3: Time domain snippet ---
figure('Name', '05c - IQ Time Domain', 'Position', [100 550 1000 350]);
t_ms = (0:4999) / FS * 1000;
plot(t_ms, I(1:5000), 'b', 'LineWidth', 0.5); hold on;
plot(t_ms, Q(1:5000), 'r', 'LineWidth', 0.5);
xlabel('Time (ms)'); ylabel('Amplitude');
title('IQ Time Domain — first 5000 samples (2.5 ms)');
legend('I','Q'); grid on;
yline(0, 'k--', 'LineWidth', 0.5);

%% --- Interpretation ---
fprintf('\n--- Constellation Interpretation ---\n');
fprintf('Healthy GPS L1 C/A capture should show:\n');
fprintf('  - Circular Gaussian cloud centered at origin\n');
fprintf('  - Equal I and Q spread (IQ imbalance <5%%)\n');
fprintf('  - Cloud center at (0,0) — no DC bias\n');
fprintf('\nYour capture:\n');

if dc_offset < 0.05 * mean([I_std Q_std])
    fprintf('  DC offset: GOOD — cloud near origin\n');
elseif dc_offset < 0.2 * mean([I_std Q_std])
    fprintf('  DC offset: MODERATE — some DC bias visible\n');
else
    fprintf('  DC offset: HIGH — cloud shifted from origin, zero-IF contamination\n');
end

if iq_imbalance < 2
    fprintf('  IQ balance: GOOD — I and Q channels well matched\n');
elseif iq_imbalance < 5
    fprintf('  IQ balance: ACCEPTABLE — minor mismatch\n');
else
    fprintf('  IQ balance: POOR — significant I/Q amplitude mismatch\n');
    fprintf('              This can cause image rejection problems\n');
end

fprintf('\nNote: GPS L1 C/A is spread spectrum — the constellation\n');
fprintf('should always look like noise (circular cloud), not a\n');
fprintf('structured pattern like QPSK. Structure in the cloud\n');
fprintf('indicates interference or spurious signals.\n');
