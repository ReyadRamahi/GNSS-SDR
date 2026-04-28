# Current Local F9T Helper Scripts

These scripts support the current `hft02` local-F9T workflow.

- `enable_f9t_ubx_uart1.py`
  - enables the needed UBX protocol and message outputs on the local F9T
- `refresh_f9t_xml_local.sh`
  - captures local F9T data, converts it, and refreshes the latest assistance XML
- `start_f9t_refresh_local_tmux.sh`
  - tmux wrapper for longer unattended refreshes

This is the active assistance-refresh path for the current Lime work.
