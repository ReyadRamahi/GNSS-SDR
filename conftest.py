import sys
from pathlib import Path

# Ensure the project root is on sys.path so tests can import nmea_parser, map_aid, etc.
sys.path.insert(0, str(Path(__file__).parent))
