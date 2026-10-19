"""Run the addon integration and regression suites with Lua 5.1."""
from pathlib import Path
import runpy
import sys
sys.path.insert(0,str(Path(__file__).parent))
runpy.run_path(str(Path(__file__).with_name("test_health_regressions.py")),run_name="__main__")
