% =========================================================
% 06_iq_correct.m
% Apply manual DC offset removal and IQ amplitude correction
% to a raw Lime IQ capture and save a corrected .dat file
%
% Corrections applied:
%   1. Remove DC offset from I and Q channels
%   2. Scale Q channel to match I channel amplitude
%
% The corrected file can then be fed into GNSS-SDR using
% File_Signal_Source instead of the live LimeSDR.
%
% Usage:
%   Set IQ_FILE_IN to your raw capture
%   Run the script
%   Use the output file with gnss_sdr_file_source.conf
% =========================================================

clear; close all; clc;

%% --- Configuration ---
IQ_FILE_IN  = 'lime_iq_capture_calibrated.dat';   % input raw file
IQ_FILE_OUT = 'lime_iq_corrected.dat';             % output corrected file

% How many samples to use for estimating correction parameters
% Use first 1 second (skip the DC calibration transient at start)
FS              = 2e6;
SKIP_SAMPLES    = round(0.001 * FS);   % skip first 1ms (transient)
ESTIMATE_SAMPLES = round(1.0 * FS);    % use 1 second for estimation

%% --- Load full file for correction ---
fprintf('Getting file size...\n');
d = dir(IQ_FILE_IN);
total_samples = floor(d.bytes / 8);   % 2x float32 = 8 bytes per sample
fprintf('Total samples in file: %d (%.1f seconds)\n', total_samples, total_samples/FS);

%% --- Load estimation window ---
fprintf('Loading estimation window...\n');
fid = fopen(IQ_FILE_IN, 'rb');
if fid == -1, error('Cannot open: %s', IQ_FILE_IN); end

% Skip transient
fseek(fid, SKIP_SAMPLES * 8, 'bof');

% Read estimation block
raw_est = fread(fid, ESTIMATE_SAMPLES * 2, 'float32');
fclose(fid);

I_est = raw_est(1:2:end);
Q_est = raw_est(2:2:end);

%% --- Compute correction parameters ---
I_mean  = mean(I_est);
Q_mean  = mean(Q_est);
I_std   = std(I_est);
Q_std   = std(Q_est);
Q_scale = I_std / Q_std;   % scale Q down to match I amplitude

fprintf('\n--- Correction Parameters ---\n');
fprintf('I DC offset:   %+.6f  (will be removed)\n', I_mean);
fprintf('Q DC offset:   %+.6f  (will be removed)\n', Q_mean);
fprintf('I std dev:     %.6f\n', I_std);
fprintf('Q std dev:     %.6f\n', Q_std);
fprintf('Q scale factor: %.6f  (Q will be multiplied by this)\n', Q_scale);
fprintf('Expected IQ imbalance after correction: <1%%\n');

%% --- Apply correction to full file in chunks ---
CHUNK_SAMPLES = 1e6;   % process 1M samples at a time to avoid memory issues
n_chunks = ceil(total_samples / CHUNK_SAMPLES);

fprintf('\nApplying correction to full file (%d chunks)...\n', n_chunks);

fid_in  = fopen(IQ_FILE_IN,  'rb');
fid_out = fopen(IQ_FILE_OUT, 'wb');

if fid_in  == -1, error('Cannot open input:  %s', IQ_FILE_IN);  end
if fid_out == -1, error('Cannot open output: %s', IQ_FILE_OUT); end

samples_written = 0;
for c = 1:n_chunks
    raw = fread(fid_in, CHUNK_SAMPLES * 2, 'float32');
    if isempty(raw), break; end
    
    I_chunk = raw(1:2:end);
    Q_chunk = raw(2:2:end);
    
    % Apply corrections
    I_corrected = I_chunk - I_mean;
    Q_corrected = (Q_chunk - Q_mean) * Q_scale;
    
    % Interleave and write
    out = zeros(length(I_corrected) * 2, 1, 'single');
    out(1:2:end) = single(I_corrected);
    out(2:2:end) = single(Q_corrected);
    fwrite(fid_out, out, 'float32');
    
    samples_written = samples_written + length(I_corrected);
    if mod(c, 5) == 0
        fprintf('  Processed %d / %d samples (%.0f%%)\n', ...
            samples_written, total_samples, samples_written/total_samples*100);
    end
end

fclose(fid_in);
fclose(fid_out);

fprintf('Done. Written %d samples to %s\n', samples_written, IQ_FILE_OUT);

%% --- Verify correction ---
fprintf('\nVerifying correction...\n');
fid = fopen(IQ_FILE_OUT, 'rb');
fseek(fid, SKIP_SAMPLES * 8, 'bof');
raw_check = fread(fid, ESTIMATE_SAMPLES * 2, 'float32');
fclose(fid);

I_check = raw_check(1:2:end);
Q_check = raw_check(2:2:end);

I_mean_after  = mean(I_check);
Q_mean_after  = mean(Q_check);
I_std_after   = std(I_check);
Q_std_after   = std(Q_check);
imbalance_after = abs(I_std_after - Q_std_after) / mean([I_std_after Q_std_after]) * 100;
power_ratio_db  = 10*log10(mean(I_check.^2) / mean(Q_check.^2));

fprintf('\n--- Verification ---\n');
fprintf('%-25s  %-12s  %-12s\n', 'Metric', 'Before', 'After');
fprintf('%-25s  %-12.4f  %-12.4f\n', 'I DC offset', I_mean, I_mean_after);
fprintf('%-25s  %-12.4f  %-12.4f\n', 'Q DC offset', Q_mean, Q_mean_after);
fprintf('%-25s  %-12.4f  %-12.4f\n', 'I std dev', I_std, I_std_after);
fprintf('%-25s  %-12.4f  %-12.4f\n', 'Q std dev', Q_std, Q_std_after);
fprintf('%-25s  %-12.2f  %-12.2f\n', 'IQ imbalance (%)', ...
    abs(I_std-Q_std)/mean([I_std Q_std])*100, imbalance_after);
fprintf('%-25s  %-12.3f  %-12.3f\n', 'Power ratio I/Q (dB)', ...
    10*log10(mean(I_est.^2)/mean(Q_est.^2)), power_ratio_db);

if imbalance_after < 5
    fprintf('\nRESULT: PASS — IQ imbalance corrected to %.2f%%\n', imbalance_after);
    fprintf('Next step: run GNSS-SDR with lime_gnss_sdr_file_source.conf\n');
    fprintf('pointing at: %s\n', IQ_FILE_OUT);
else
    fprintf('\nRESULT: WARNING — IQ imbalance still %.2f%% after correction\n', imbalance_after);
    fprintf('Check that the estimation window is not contaminated by the DC transient\n');
end

%% --- Quick constellation check ---
N_PLOT = 50000;
idx = round(linspace(1, length(I_check), min(N_PLOT, length(I_check))));

figure('Name', '06 - Corrected IQ Constellation', 'Position', [100 100 700 700]);
histogram2(I_check(idx), Q_check(idx), 200, ...
    'DisplayStyle', 'tile', 'ShowEmptyBins', 'off');
colormap(jet); colorbar; axis equal;
xlabel('I (In-phase)'); ylabel('Q (Quadrature)');
title(sprintf('Corrected IQ Constellation\nIQ imbalance: %.2f%%  (was 122.8%%)', imbalance_after));
grid on;
hold on;
plot(0, 0, 'w+', 'MarkerSize', 12, 'LineWidth', 2);
plot(I_mean_after, Q_mean_after, 'rx', 'MarkerSize', 12, 'LineWidth', 2);
legend('', 'Origin (0,0)', 'DC center', 'Location', 'northeast');
