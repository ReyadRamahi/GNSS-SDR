% =========================================================
% 03_tracking_sim.m
% Simulate a PLL/DLL tracking loop on raw IQ
%
% This tells you:
%   - how long the tracking loop can hold lock on the raw IQ
%   - what the PLL discriminator output looks like over time
%   - whether the phase error is drifting (clock problem) or
%     jumping randomly (noise problem)
%
% Run 02_prn_correlation.m first to find which PRN has the
% best correlation peak and what its Doppler offset is.
% Enter those values in the configuration below.
%
% Usage:
%   Set IQ_FILE, PRN, and DOPPLER_HZ from 02 results
%   Run the script
% =========================================================

clear; close all; clc;

%% --- Configuration ---
IQ_FILE     = 'lime_iq_capture.dat';
FS          = 2e6;          % sample rate Hz
CODE_RATE   = 1.023e6;      % chip rate Hz
CODE_LEN    = 1023;

% Set these from 02_prn_correlation.m results
PRN         = 27;           % PRN with best correlation peak
DOPPLER_HZ  = -4000;            % Doppler estimate from 02 (Hz) - update this

% Tracking loop parameters (match your GNSS-SDR config)
PLL_BW      = 40;           % Hz
DLL_BW      = 2;            % Hz
INTEG_MS    = 1;            % coherent integration ms

% How long to run the simulation
SIM_DURATION_MS = 2000;     % 2 seconds

%% --- Load IQ ---
N_LOAD = SIM_DURATION_MS * round(FS * 1e-3) + 1000;
fprintf('Loading %d samples...\n', N_LOAD);
fid = fopen(IQ_FILE, 'rb');
if fid == -1, error('Cannot open: %s', IQ_FILE); end
raw = fread(fid, N_LOAD * 2, 'float32');
fclose(fid);
iq = raw(1:2:end) + 1j * raw(2:2:end);

%% --- Generate PRN ---
function code = generate_prn(prn)
    G2_taps = [
        [2,6]; [3,7]; [4,8]; [5,9]; [1,9]; [2,10]; [1,8]; [2,9];
        [3,10]; [2,3]; [3,4]; [5,6]; [6,7]; [7,8]; [8,9]; [9,10];
        [1,4]; [2,5]; [3,6]; [4,7]; [5,8]; [6,9]; [1,3]; [4,6];
        [5,7]; [6,8]; [7,9]; [8,10]; [1,6]; [2,7]; [3,8]; [4,9];
    ];
    g1 = ones(1,10); g2 = ones(1,10);
    code = zeros(1,1023);
    tap = G2_taps(prn, :);
    for i = 1:1023
        code(i) = xor(g1(10), xor(g2(tap(1)), g2(tap(2))));
        g1_new = xor(g1(3), g1(10));
        g2_new = xor(g2(2), xor(g2(3), xor(g2(6), xor(g2(8), xor(g2(9), g2(10))))));
        g1 = [g1_new g1(1:9)];
        g2 = [g2_new g2(1:9)];
    end
    code = 1 - 2*code;
end

samples_per_ms  = round(FS * 1e-3);
samples_per_chip = FS / CODE_RATE;
chip_idx = floor((0:samples_per_ms-1) / samples_per_chip);
chip_idx = mod(chip_idx, CODE_LEN);
code_chips = generate_prn(PRN);

%% --- Loop filter coefficients (2nd order PLL) ---
% Bandwidth to loop filter natural frequency
pll_wn = PLL_BW * 8 / (sqrt(2) * 8 + 4 * 1);
dll_wn = DLL_BW * 8 / (sqrt(2) * 8 + 4 * 1);

T = INTEG_MS * 1e-3;
pll_a2 = 1.414 * pll_wn;
pll_a3 = pll_wn^2;
dll_a2 = 1.414 * dll_wn;

%% --- Tracking loop simulation ---
fprintf('Simulating tracking loop for PRN G%02d...\n', PRN);

% State variables
carrier_phase   = 0;
carrier_freq    = DOPPLER_HZ;
carrier_freq_rate = 0;
code_phase      = 0;   % chips
code_freq       = CODE_RATE;

pll_integrator  = 0;
dll_integrator  = 0;

% Output buffers
n_steps = floor(SIM_DURATION_MS / INTEG_MS);
out_I_prompt    = zeros(1, n_steps);
out_Q_prompt    = zeros(1, n_steps);
out_pll_disc    = zeros(1, n_steps);
out_dll_disc    = zeros(1, n_steps);
out_carrier_freq = zeros(1, n_steps);
out_lock        = zeros(1, n_steps);

HALF_CHIP = 0.5;

for k = 1:n_steps
    % Sample indices for this integration period
    start_samp = (k-1) * samples_per_ms + 1;
    end_samp   = start_samp + samples_per_ms - 1;
    if end_samp > length(iq), break; end
    
    block = iq(start_samp:end_samp);
    t_block = ((0:samples_per_ms-1) + (k-1)*samples_per_ms)' / FS;
    
    % Carrier wipeoff
    carrier = exp(-1j * (2*pi*carrier_freq*t_block + carrier_phase));
    block_wiped = block .* carrier;
    
    % Code generation: prompt, early, late
    chip_times = ((0:samples_per_ms-1) * code_freq / FS + code_phase);
    
    prompt_idx = mod(floor(chip_times), CODE_LEN) + 1;
    early_idx  = mod(floor(chip_times - HALF_CHIP), CODE_LEN) + 1;
    late_idx   = mod(floor(chip_times + HALF_CHIP), CODE_LEN) + 1;
    
    code_prompt = code_chips(prompt_idx)';
    code_early  = code_chips(early_idx)';
    code_late   = code_chips(late_idx)';
    
    % Correlators
    IP = real(sum(block_wiped .* code_prompt));
    QP = imag(sum(block_wiped .* code_prompt));
    IE = real(sum(block_wiped .* code_early));
    IL = real(sum(block_wiped .* code_late));
    
    % PLL discriminator (atan)
    pll_disc = atan2(QP, IP) / (2*pi);
    
    % DLL discriminator (normalized early-minus-late)
    dll_disc = (abs(IE) - abs(IL)) / (abs(IE) + abs(IL) + 1e-10);
    
    % Lock detector (I/Q ratio)
    lock_indicator = abs(IP) / (abs(IP) + abs(QP) + 1e-10);
    
    % PLL loop filter update
    pll_integrator   = pll_integrator + pll_a3 * T * pll_disc;
    carrier_freq     = carrier_freq + pll_a2 * pll_disc + pll_integrator;
    carrier_phase    = carrier_phase + 2*pi*carrier_freq*T;
    
    % DLL loop filter update
    dll_integrator  = dll_integrator + dll_a2 * T * dll_disc;
    code_freq       = CODE_RATE + dll_integrator;
    code_phase      = mod(code_phase + code_freq * T, CODE_LEN);
    
    % Store
    out_I_prompt(k)     = IP;
    out_Q_prompt(k)     = QP;
    out_pll_disc(k)     = pll_disc;
    out_dll_disc(k)     = dll_disc;
    out_carrier_freq(k) = carrier_freq;
    out_lock(k)         = lock_indicator;
end

time_ms = (1:n_steps) * INTEG_MS;

%% --- Plots ---
figure('Name', '03 - Tracking Loop Simulation', 'Position', [100 100 1000 900]);

subplot(4,1,1);
plot(time_ms, out_I_prompt, 'b', time_ms, out_Q_prompt, 'r');
xlabel('Time (ms)'); ylabel('Amplitude');
title(sprintf('G%02d Prompt Correlator — I (blue) and Q (red)', PRN));
legend('I','Q'); grid on;
% Q should be near zero when locked

subplot(4,1,2);
plot(time_ms, out_pll_disc, 'k');
xlabel('Time (ms)'); ylabel('Phase error (cycles)');
title('PLL Discriminator Output');
yline(0.25, 'r--', 'Lock limit'); yline(-0.25, 'r--');
grid on;
% If this drifts monotonically -> clock/frequency problem
% If this jumps randomly -> noise problem

subplot(4,1,3);
plot(time_ms, out_carrier_freq, 'm');
xlabel('Time (ms)'); ylabel('Frequency (Hz)');
title('Carrier Frequency Estimate (Doppler)');
grid on;
% Should converge to a stable value if locked

subplot(4,1,4);
plot(time_ms, out_lock, 'g');
xlabel('Time (ms)'); ylabel('Lock indicator (0-1)');
title('Lock Indicator (>0.7 = locked, <0.5 = lost)');
yline(0.7, 'g--', 'Locked'); yline(0.5, 'r--', 'Lost');
ylim([0 1]); grid on;

sgtitle(sprintf('Tracking Loop Simulation — PRN G%02d  PLL BW=%.0f Hz', PRN, PLL_BW));

%% --- Summary ---
locked_frac = mean(out_lock > 0.7);
fprintf('\n--- Tracking Simulation Summary ---\n');
fprintf('PRN:              G%02d\n', PRN);
fprintf('Simulation time:  %d ms\n', n_steps * INTEG_MS);
fprintf('Fraction locked:  %.1f%%\n', locked_frac * 100);

if locked_frac > 0.8
    fprintf('Result: STABLE LOCK - signal quality is sufficient\n');
    fprintf('        If GNSS-SDR still fails, problem is elsewhere\n');
elseif locked_frac > 0.4
    fprintf('Result: INTERMITTENT LOCK - signal is marginal\n');
    fprintf('        C/N0 is borderline, hardware filter may help\n');
else
    fprintf('Result: CANNOT HOLD LOCK - signal too weak\n');
    fprintf('        Hardware bandpass filter is needed\n');
end

% Diagnose: is it a drift or noise problem?
pll_trend = polyfit(time_ms, out_pll_disc, 1);
if abs(pll_trend(1)) > 0.001
    fprintf('\nDIAGNOSIS: PLL discriminator is DRIFTING (slope=%.4f cyc/ms)\n', pll_trend(1));
    fprintf('           This suggests a FREQUENCY/CLOCK problem\n');
else
    fprintf('\nDIAGNOSIS: PLL discriminator is NOT drifting\n');
    fprintf('           Loss of lock is due to NOISE, not clock error\n');
end
