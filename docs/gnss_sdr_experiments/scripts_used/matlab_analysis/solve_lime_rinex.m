function fixes = solve_lime_rinex(runDir)
%SOLVE_LIME_RINEX Solve GPS L1 positions from a GNSS-SDR RINEX export.
%   Pass the six-channel replay output directory. Requires Navigation Toolbox.

obs = rinexread(fullfile(runDir, 'lime_l1.26O'));
[nav, header] = rinexread(fullfile(runDir, 'lime_l1.26N'));
measurements = gnssmeasurements(obs.GPS, nav.GPS, "C1C");

corrections = header.IonosphericCorrections;
options = gnssoptions(Troposphere=gnssTroposphere("saastamoinen"));
if numel(corrections) >= 2
    options.Ionosphere = gnssIonosphere("klobuchar", ...
        corrections(1).Parameters, corrections(2).Parameters);
end
[lla, ~, hdop, vdop] = receiverposition(measurements, options);
epochs = unique(measurements.Properties.RowTimes);
assert(numel(epochs) == size(lla, 1), ...
    'Unexpected mismatch between measurement epochs and position solutions.');

valid = all(isfinite(lla), 2) & all(isfinite([hdop, vdop]), 2);
assert(any(valid), 'MATLAB did not produce any finite position solutions.');
fixes = timetable(epochs(valid), lla(valid, 1), lla(valid, 2), lla(valid, 3), ...
    hdop(valid), vdop(valid), 'VariableNames', ...
    {'LatitudeDeg','LongitudeDeg','EllipsoidHeightM','HDOP','VDOP'});

center = median(lla(valid, :), 1);
fprintf('MATLAB solved %d of %d epochs.\n', nnz(valid), numel(valid));
fprintf('Median latitude %.7f deg, longitude %.7f deg, ellipsoid height %.1f m\n', center);
fprintf('Median HDOP %.2f, VDOP %.2f\n', median(hdop(valid)), median(vdop(valid)));
end
