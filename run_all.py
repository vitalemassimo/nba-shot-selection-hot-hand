"""Run the full pipeline from raw data to results, stage by stage.

Usage: python run_all.py [--stage N]
Stages that are not implemented yet are skipped with a message.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from hothand import acquire, dashboard_data
from hothand.config import ROOT, load_config


def run_notebook(name: str) -> None:
    """Execute a notebook in place, so its outputs and the files it writes are regenerated.

    Calls nbconvert as a module of this interpreter and puts this environment's bin directory first
    on PATH, so the kernel runs with the pinned packages and not another Python on the machine.
    """
    env = {**os.environ, "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"}
    subprocess.run([sys.executable, "-m", "nbconvert", "--to", "notebook", "--execute",
                    "--inplace", name], cwd=ROOT / "notebooks", check=True, env=env)


STAGES = {
    2: "acquire",
    3: "audit_and_clean",
    4: "features",
    5: "core_test",
    6: "segments",
    7: "robustness",
    8: "dashboard_data",
}

RUNNERS = {
    2: acquire.run,
    3: lambda: run_notebook("01_audit.ipynb"),
    4: lambda: run_notebook("02_features.ipynb"),
    5: lambda: run_notebook("03_core_test.ipynb"),
    6: lambda: run_notebook("04_segments.ipynb"),
    7: lambda: run_notebook("05_robustness.ipynb"),
    8: dashboard_data.run,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, choices=sorted(STAGES), help="run one stage only")
    args = parser.parse_args()

    cfg = load_config()
    print(f"Config loaded: {len(cfg['data']['seasons'])} seasons, seed {cfg['random_seed']}")
    for n, name in STAGES.items():
        if args.stage and n != args.stage:
            continue
        if n in RUNNERS:
            print(f"Stage {n} ({name}): running")
            RUNNERS[n]()
        else:
            print(f"Stage {n} ({name}): not implemented yet, skipped")


if __name__ == "__main__":
    main()
