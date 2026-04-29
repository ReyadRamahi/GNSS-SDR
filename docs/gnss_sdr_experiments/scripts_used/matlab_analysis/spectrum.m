% =========================================================
% 01_spectrum.m
% Plot power spectrum and DC spike of raw Lime IQ capture
%
% Run this first. It tells you:
%   - whether the GPS L1 band is visible
%   - how bad the DC spike is
%   - whether there is obvious interference
%
% Usage:
%   Set IQ_FILE to the path of your lime_iq_capture.dat
%   Run the script
% =========================================================

clear; close all; clc;

%% --- Configuration ---
IQ_FILE   = 'lime_iq_capture.dat';   % path to your .dat file
FS        = 2e6;                      % sample rate Hz
N_SPEC    = 2^18;                     % FFT size for spectrum (262144 points)
N_LOAD    = 2e6;                      % samples to load (1 second is enough)

%% --- Load IQ ---
fprintf('Loading IQ from: %s\n', IQ_FILE);
fid = fopen(IQ_FILE, 'rb');
if fid == -1
    error('Cannot open file: %s', IQ_FILE);
end
raw = fread(fid, N_LOAD * 2, 'float32');
fclose(fid);

% Interleaved float32: [I0 Q0 I1 Q1 ...]
iq = raw(1:2:end) + 1j * raw(2:2:end);
fprintf('Loaded %d samples (%.1f seconds)\n', length(iq), length(iq)/FS);

%% --- Power Spectrum ---
fprintf('Computing power spectrum...\n');
[pxx, f] = pwelch(iq, hanning(N_SPEC), N_SPEC/2, N_SPEC, FS, 'centered');
f_mhz = f / 1e6;
pxx_db = 10*log10(pxx);

figure('Name', '01 - Power Spectrum', 'Position', [100 100 900 400]);
plot(f_mhz, pxx_db, 'b', 'LineWidth', 0.8);
xlabel('Frequency offset from LO (MHz)');
ylabel('Power (dB)');
title('Lime IQ Power Spectrum (centered on L1 = 1575.42 MHz)');
grid on;
xlim([-1 1]);
ylim([min(pxx_db)-5 max(pxx_db)+5]);

% Mark DC
hold on;
xline(0, 'r--', 'DC (LO leakage)', 'LineWidth', 1.5, 'LabelVerticalAlignment', 'bottom');

% Mark GPS L1 C/A bandwidth (~2 MHz centered)
xline(-0.511, 'g--', 'GPS edge', 'LineWidth', 1, 'LabelVerticalAlignment', 'top');
xline( 0.511, 'g--', 'GPS edge', 'LineWidth', 1, 'LabelVerticalAlignment', 'top');

fprintf('\n--- Spectrum Summary ---\n');
fprintf('Noise floor (approx):  %.1f dB\n', median(pxx_db));
fprintf('Peak power:            %.1f dB\n', max(pxx_db));

% DC spike measurement
dc_bin = find(abs(f) == min(abs(f)));
dc_power = pxx_db(dc_bin);
noise_floor = median(pxx_db);
fprintf('DC spike power:        %.1f dB\n', dc_power);
fprintf('DC spike above floor:  %.1f dB\n', dc_power - noise_floor);

if dc_power - noise_floor > 20
    fprintf('WARNING: DC spike is >20 dB above floor - significant zero-IF contamination\n');
elseif dc_power - noise_floor > 10
    fprintf('CAUTION: DC spike is 10-20 dB above floor - moderate zero-IF contamination\n');
else
    fprintf('OK: DC spike is <10 dB above floor - minimal zero-IF contamination\n');
end

%% --- Zoomed DC view ---
figure('Name', '01b - DC Spike Zoom', 'Position', [100 550 900 300]);
mask = abs(f) < 0.1e6;
plot(f(mask)/1e3, pxx_db(mask), 'b', 'LineWidth', 1);
xlabel('Frequency offset from LO (kHz)');
ylabel('Power (dB)');
title('DC Spike Detail (±100 kHz around LO)');
grid on;
xline(0, 'r--', 'DC', 'LineWidth', 1.5);
