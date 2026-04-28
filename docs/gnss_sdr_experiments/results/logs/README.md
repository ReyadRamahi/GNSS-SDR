# Logs

This folder groups logs and run summaries by experiment family.

## Subfolders

- `baseline_runs/`
  - early Lime and RTL baseline logs that were previously under the generic `output/` folder
- `f9t_lime_current/`
  - most relevant current summaries for the active Lime tracking issue
- `f9t_refresh/`
  - refresh logs from the older `hft09` TCP assistance path
- `lime_sweeps/`
  - parameter-sweep runs split into `v1/`, `v2/`, and `v3/`
- `rtl_harvest/`
  - RTL harvest logs tied to earlier assistance generation
- `rtl_track/`
  - RTL reference tracking summaries proving the pipeline can decode NAV

For the current Lime bottleneck, start with `f9t_lime_current/`.
