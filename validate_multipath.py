"""
validate_multipath.py
Standalone validation script for the specular multipath model in map_aid.py.

Uses the Google Smartphone Decimeter Challenge 2022 dataset to test whether
predicted reflection_delay_m correlates with real-world pseudorange errors.

Usage:
    py -3 validate_multipath.py \\
        --gnss-log     kaggle_data/gnss_log.txt \\
        --ground-truth kaggle_data/ground_truth.csv \\
        --device-gnss  kaggle_data/device_gnss.csv \\
        --output       validation_report.json \\
        --max-epochs   200

No server, no frontend — runs entirely from the command line.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is importable when script is run directly
sys.path.insert(0, str(Path(__file__).parent))

from kaggle_adapter import KaggleGnssAdapter
from map_aid import BuildingMask, _SAT_DIST_M


# ---------------------------------------------------------------------------
# Pure-stdlib math helpers
# ---------------------------------------------------------------------------

def pearson_correlation(xs: list[float], ys: list[float]) -> float:
    """Pearson r — returns 0.0 if fewer than 2 pairs or zero variance."""
    if len(xs) < 2:
        return 0.0
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(
        sum((x - mx) ** 2 for x in xs) *
        sum((y - my) ** 2 for y in ys)
    )
    return num / den if den > 0.0 else 0.0


def rmse(errors: list[float]) -> float:
    """Root-mean-square error. Returns 0.0 for an empty list."""
    if not errors:
        return 0.0
    return math.sqrt(sum(e ** 2 for e in errors) / len(errors))


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate horizontal distance between two WGS-84 points (metres)."""
    R = 6_371_000.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

def _position_rmse(adapter: KaggleGnssAdapter) -> float:
    """Horizontal RMSE between phone-reported and ground-truth positions (m)."""
    device = adapter.get_device_positions()
    if not device:
        return 0.0

    gt_by_time: dict[str, tuple[float, float]] = {
        p["time"]: (p["lat"], p["lon"])
        for p in adapter.get_ground_truth_positions()
    }

    errors: list[float] = []
    for fix in device:
        gt = gt_by_time.get(fix["time"])
        if gt is None:
            continue
        errors.append(_haversine_m(fix["lat"], fix["lon"], gt[0], gt[1]))

    return rmse(errors)


def run_validation(
    gnss_log: str,
    ground_truth: str,
    device_gnss: Optional[str],
    output: str,
    max_epochs: Optional[int],
) -> dict:
    # ------------------------------------------------------------------
    # Load dataset
    # ------------------------------------------------------------------
    print("Loading dataset...")
    adapter = KaggleGnssAdapter(gnss_log, ground_truth, device_gnss)

    all_epochs = adapter.get_epochs()
    print(f"  Epochs: {len(all_epochs)}")

    epochs = all_epochs[:max_epochs] if max_epochs else all_epochs

    total_sats = sum(len(adapter.get_satellites(e)) for e in epochs)
    print(f"  Satellite measurements: {total_sats}")

    # ------------------------------------------------------------------
    # Initialise building mask from first available ground-truth position
    # ------------------------------------------------------------------
    mask: Optional[BuildingMask] = None
    receiver_lat = receiver_lon = 0.0
    building_count = 0

    for ep in epochs:
        pos = adapter.get_position(ep)
        if pos is not None:
            receiver_lat = pos["lat"]
            receiver_lon = pos["lon"]
            break

    if receiver_lat != 0.0 or receiver_lon != 0.0:
        print(f"Initialising building mask at ({receiver_lat:.4f}, {receiver_lon:.4f})...")
        mask = BuildingMask(receiver_lat, receiver_lon)
        building_count = mask.building_count
        print(f"  Buildings loaded: {building_count}")
    else:
        print("WARNING: No ground-truth position found — skipping building mask.")

    # ------------------------------------------------------------------
    # Per-epoch processing
    # ------------------------------------------------------------------
    predicted_delays: list[float] = []   # reflection_delay_m for has_reflection sats
    actual_errors_refl: list[float] = [] # pseudorange errors for has_reflection sats
    actual_errors_los: list[float] = []  # pseudorange errors for clean LOS sats

    cn0_nlos: list[float] = []
    cn0_los:  list[float] = []

    num_sat_measurements = 0

    for i, epoch_ms in enumerate(epochs):
        if (i + 1) % 50 == 0 or (i + 1) == len(epochs):
            print(f"Processing epochs: {i + 1}/{len(epochs)}", end="\r", flush=True)

        sats     = adapter.get_satellites(epoch_ms)
        prs      = adapter.get_pseudoranges(epoch_ms)
        num_sat_measurements += len(sats)

        if not sats or mask is None:
            continue

        # classify_satellites expects list[dict] with elevation_deg, azimuth_deg, prn, cn0
        sat_input = [
            {
                "prn":           s["prn"],
                "elevation_deg": s["elevation_deg"],
                "azimuth_deg":   s["azimuth_deg"],
                "cn0":           s["cn0"],
            }
            for s in sats
        ]
        classified = mask.classify_satellites(sat_input)
        by_prn = {c["prn"]: c for c in classified}

        for sat in sats:
            prn  = sat["prn"]
            info = by_prn.get(prn)
            if info is None:
                continue

            pr = prs.get(prn)

            if info.get("has_reflection"):
                cn0_nlos.append(sat["cn0"])
                if pr is not None:
                    actual_err = pr - _SAT_DIST_M
                    predicted_delays.append(info["reflection_delay_m"])
                    actual_errors_refl.append(actual_err)
            elif info.get("predicted_los"):
                cn0_los.append(sat["cn0"])
                if pr is not None:
                    actual_err = pr - _SAT_DIST_M
                    actual_errors_los.append(actual_err)
            else:
                # NLOS — track CN0 for CN0 validation block
                cn0_nlos.append(sat["cn0"])

    print()  # newline after \r progress

    # ------------------------------------------------------------------
    # Compute metrics
    # ------------------------------------------------------------------
    phone_rmse = _position_rmse(adapter)

    corr = pearson_correlation(predicted_delays, actual_errors_refl)

    mean_pred   = statistics.mean(predicted_delays)   if predicted_delays   else 0.0
    mean_refl   = statistics.mean(actual_errors_refl) if actual_errors_refl else 0.0
    mean_los    = statistics.mean(actual_errors_los)  if actual_errors_los  else 0.0
    rmse_refl   = rmse(actual_errors_refl)
    rmse_los    = rmse(actual_errors_los)
    mean_cn0_nlos = statistics.mean(cn0_nlos) if cn0_nlos else 0.0
    mean_cn0_los  = statistics.mean(cn0_los)  if cn0_los  else 0.0

    model_working = corr > 0.0 and mean_refl > mean_los

    # ------------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------------
    report: dict = {
        "dataset_info": {
            "gnss_log":                  gnss_log,
            "num_epochs_processed":      len(epochs),
            "num_satellite_measurements": num_sat_measurements,
            "receiver_lat":              receiver_lat,
            "receiver_lon":              receiver_lon,
            "building_count":            building_count,
        },
        "position_accuracy": {
            "phone_rmse_m": round(phone_rmse, 2),
            "note": "RMS error of phone-reported position vs ground truth",
        },
        "multipath_model_validation": {
            "num_satellites_with_reflection": len(predicted_delays),
            "num_satellites_clean_los":       len(actual_errors_los),
            "pearson_correlation":            round(corr, 4),
            "note": (
                "Correlation between predicted reflection_delay_m and actual "
                "pseudorange error. >0 means model works, closer to 1.0 is better."
            ),
            "mean_predicted_delay_reflection_m": round(mean_pred,  2),
            "mean_actual_error_reflection_m":     round(mean_refl,  2),
            "mean_actual_error_los_m":            round(mean_los,   2),
            "rmse_reflection_satellites_m":       round(rmse_refl,  2),
            "rmse_los_satellites_m":              round(rmse_los,   2),
        },
        "cn0_validation": {
            "mean_cn0_predicted_nlos": round(mean_cn0_nlos, 2),
            "mean_cn0_predicted_los":  round(mean_cn0_los,  2),
            "note": "Lower CN0 for predicted NLOS confirms signal quality degradation",
        },
        "interpretation": {
            "model_working": model_working,
            "reason": (
                "pearson_correlation > 0 and mean_actual_error_reflection_m > "
                "mean_actual_error_los_m"
            ),
        },
    }

    # ------------------------------------------------------------------
    # Write output and print summary
    # ------------------------------------------------------------------
    print(f"Writing {output}...")
    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")

    yn = "YES" if model_working else "NO"
    print(f"""
Results:
  Phone RMSE:            {phone_rmse:.1f} m
  Pearson correlation:   {corr:.4f}
  Reflection mean error: {mean_refl:.1f} m
  Clean LOS mean error:  {mean_los:.1f} m
  Model working:         {yn}
""")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Validate specular multipath model against Kaggle GSDC-2022 dataset."
    )
    p.add_argument("--gnss-log",     required=True, help="Path to gnss_log.txt")
    p.add_argument("--ground-truth", required=True, help="Path to ground_truth.csv")
    p.add_argument("--device-gnss",  default=None,  help="Path to device_gnss.csv (optional)")
    p.add_argument("--output",       default="validation_report.json",
                   help="Output JSON path (default: validation_report.json)")
    p.add_argument("--max-epochs",   type=int, default=None,
                   help="Limit number of epochs processed (default: all)")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_validation(
        gnss_log=args.gnss_log,
        ground_truth=args.ground_truth,
        device_gnss=args.device_gnss,
        output=args.output,
        max_epochs=args.max_epochs,
    )
