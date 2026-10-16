"""Displayed-vs-CSV check (playbook 8.5): run the app headlessly and compare every number it shows
on the Headline and Explorer tabs with the committed results tables. Run before every deploy:
    python dashboard/check_numbers.py
"""

import sys
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"


def main() -> int:
    core = pd.read_csv(P / "results_core.csv")
    ex = pd.read_csv(P / "dashboard" / "explorer.csv")
    m3 = core[(core.model == "Model 3") & (core.treatment == "prev_made")].set_index("outcome")
    perm = core[(core.method == "permutation") & (core.within == "game_id+player_id")].set_index("outcome")
    expected = {
        "Shift in distance": f"{m3.loc['distance_vs_baseline_ft', 'estimate']:.2f} ft",
        "Shift in three-point share": f"{100 * m3.loc['rel_three', 'estimate']:+.1f} pp",
        "Make probability after a make": f"{100 * perm.loc['next_surprise', 'estimate']:+.1f} pp",
    }
    failures = []
    at = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=120).run()
    if at.exception:
        print("app raised:", at.exception)
        return 1
    shown = {m.label: m.value for m in at.metric}
    for label, value in expected.items():
        if shown.get(label) != value:
            failures.append(f"{label}: shown {shown.get(label)!r}, CSV {value!r}")

    # Explorer: every group x outcome combination
    for _, r in ex[ex.status == "estimated"].iterrows():
        at.selectbox(key="explorer_group").set_value(r.group)
        at.selectbox(key="explorer_outcome").set_value(r.outcome_label)
        at.run()
        unit = "ft" if r.outcome == "distance_vs_baseline_ft" else "pp"
        want = f"{r.estimate:+.2f} {unit}"
        got = {m.label: m.value for m in at.metric}.get("Shift (after a make minus after a miss)")
        if got != want:
            failures.append(f"Explorer {r.group} / {r.outcome}: shown {got!r}, CSV {want!r}")

    checked = len(expected) + int((ex.status == "estimated").sum())
    if failures:
        print("\n".join(failures))
        return 1
    print(f"OK: {checked} displayed numbers match the results tables.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
