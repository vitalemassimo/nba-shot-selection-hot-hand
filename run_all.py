"""Run the full pipeline from raw data to results, stage by stage.

Usage: python run_all.py [--stage N]
Stages that are not implemented yet are skipped with a message.
"""

import argparse

from hothand.config import load_config

STAGES = {
    2: "acquire",
    3: "audit_and_clean",
    4: "features",
    5: "core_test",
    6: "segments",
    7: "robustness",
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
        print(f"Stage {n} ({name}): not implemented yet, skipped")


if __name__ == "__main__":
    main()
