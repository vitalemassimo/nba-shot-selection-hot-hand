"""NBA shot selection after makes and misses: interactive dashboard (Stage 8).

Reads only pre-aggregated tables in data/processed/ and never computes a result itself (playbook
8.2). All wording comes from dashboard/text.yaml (Massimo's). Run: streamlit run dashboard/app.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DASH = PROCESSED / "dashboard"
TEXT = yaml.safe_load((Path(__file__).parent / "text.yaml").read_text())

MAKE, MISS = "#1f77b4", "#d95f02"  # colour-blind-safe pair (blue / orange)


@st.cache_data
def load():
    return {
        "core": pd.read_csv(PROCESSED / "results_core.csv"),
        "explorer": pd.read_csv(DASH / "explorer.csv"),
        "shotmap": pd.read_csv(DASH / "shotmap.csv"),
        "players": pd.read_csv(DASH / "players.csv"),
    }


def source(*tables: str) -> None:
    st.caption("Source: " + ", ".join(f"`{t}`" for t in tables) + " (analysis half of games).")


def headline_numbers(core: pd.DataFrame) -> dict:
    m3 = core[(core.model == "Model 3") & (core.treatment == "prev_made")].set_index("outcome")
    perm = core[(core.method == "permutation") & (core.outcome == "next_surprise")]
    perm = perm.set_index("within")
    return {"shift_ft": m3.loc["distance_vs_baseline_ft"],
            "threes_pp": m3.loc["rel_three"],
            "make_prob_game": perm.loc["game_id+player_id"],
            "make_prob_quarter": perm.loc["game_id+player_id+period"]}


def forest(ex: pd.DataFrame) -> go.Figure:
    d = ex[(ex.outcome == "distance_vs_baseline_ft") & (ex.status == "estimated")
           & ~ex.group.str.contains("both contexts")].iloc[::-1]
    labels = [f"{g} ({n:,} pairs)" for g, n in zip(d.group, d.n_pairs)]
    fig = go.Figure(go.Scatter(
        x=d.estimate, y=labels, mode="markers", marker=dict(color=MAKE, size=8),
        error_x=dict(type="data", symmetric=False, array=d.ci_high - d.estimate,
                     arrayminus=d.estimate - d.ci_low, color=MAKE),
        hovertemplate="%{y}<br>shift %{x:.2f} ft<extra></extra>"))
    fig.add_vline(x=0, line_color="#999")
    fig.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=40),
                      xaxis_title="Next shot after a make minus after a miss (ft, 95% CI)")
    return fig


FT_TO_M = 0.3048


def court(fig: go.Figure, k: float = 1.0) -> None:
    """Half-court lines, basket at (0, 0), baseline at y = -5.25 ft; k scales feet to the display
    unit (1 = feet, FT_TO_M = metres)."""
    line = dict(color="#666", width=1)
    base = -5.25 * k
    t = np.linspace(np.arccos(22 / 23.75), np.pi - np.arccos(22 / 23.75), 100)
    fig.add_trace(go.Scatter(x=23.75 * k * np.cos(t), y=23.75 * k * np.sin(t), mode="lines",
                             line=line, hoverinfo="skip", showlegend=False))
    corner_y = 23.75 * k * np.sin(np.arccos(22 / 23.75))
    for x in (-22 * k, 22 * k):
        fig.add_shape(type="line", x0=x, y0=base, x1=x, y1=corner_y, line=line)
    fig.add_shape(type="rect", x0=-8 * k, y0=base, x1=8 * k, y1=base + 19 * k, line=line)
    fig.add_shape(type="circle", x0=-0.75 * k, y0=-0.75 * k, x1=0.75 * k, y1=0.75 * k, line=line)
    fig.add_shape(type="line", x0=-3 * k, y0=-1.25 * k, x1=3 * k, y1=-1.25 * k, line=line)
    t = np.linspace(0, np.pi, 50)
    fig.add_trace(go.Scatter(x=4 * k * np.cos(t), y=4 * k * np.sin(t), mode="lines", line=line,
                             hoverinfo="skip", showlegend=False))
    fig.add_shape(type="line", x0=-25 * k, y0=base, x1=25 * k, y1=base, line=line)


def shot_map(sm: pd.DataFrame, group: str, unit: str = "ft") -> go.Figure:
    k = 1.0 if unit == "ft" else FT_TO_M
    g = sm[sm.group == group]
    grid = g.pivot_table(index="y_ft", columns="x_ft", values="diff_pp")
    grid.index, grid.columns = grid.index * k, grid.columns * k
    lim = float(np.nanmax(np.abs(grid.to_numpy()))) if len(g) else 1
    fig = go.Figure(go.Heatmap(
        x=grid.columns, y=grid.index, z=grid.to_numpy(), zmin=-lim, zmax=lim, zmid=0,
        colorscale="RdBu_r", colorbar=dict(title="pp"),
        hovertemplate=f"x %{{x:.1f}} {unit}, y %{{y:.1f}} {unit} from the basket"
                      "<br>%{z:+.2f} pp<extra></extra>"))
    court(fig, k)
    fig.update_layout(height=480, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(range=[-25 * k, 25 * k], showgrid=False, zeroline=False,
                                 visible=False),
                      yaxis=dict(range=[-5.5 * k, 33 * k], showgrid=False, zeroline=False,
                                 visible=False, scaleanchor="x"))
    return fig


def explorer_chart(row: pd.Series, unit: str) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=["After a miss", "After a make"],
        y=[row.after_miss_vs_baseline, row.after_make_vs_baseline],
        marker_color=[MISS, MAKE], text=[f"{row.after_miss_vs_baseline:+.2f} {unit}",
                                          f"{row.after_make_vs_baseline:+.2f} {unit}"],
        textposition="outside"))
    fig.add_hline(y=0, line_color="#999")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis_title=f"Next shot vs own baseline ({unit})")
    return fig


def main() -> None:
    st.set_page_config(page_title="NBA shot selection", layout="centered")
    data = load()
    st.title(TEXT["title"])
    tabs = st.tabs(["Headline", "Explorer", "Shot map", "Player lookup", "Method", "Downloads"])

    with tabs[0]:
        h = headline_numbers(data["core"])
        st.subheader(TEXT["headline"]["question"])
        st.write(TEXT["headline"]["finding"])
        c1, c2, c3 = st.columns(3)
        s = h["shift_ft"]
        c1.metric("Shift in distance", f"{s.estimate:.2f} ft",
                  help=f"95% CI {s.ci_low:.2f} to {s.ci_high:.2f} ft; {int(s.n_pairs):,} pairs")
        t3 = h["threes_pp"]
        c2.metric("Shift in three-point share", f"{100 * t3.estimate:+.1f} pp",
                  help=f"95% CI {100 * t3.ci_low:+.1f} to {100 * t3.ci_high:+.1f} pp")
        with c3:  # D-053: both shuffle versions, so the card matches "no hot hand"
            st.markdown(TEXT["headline"]["make_prob_label"])
            for key, label in [("make_prob_game", "Shuffle within game"),
                               ("make_prob_quarter", "Shuffle within quarter")]:
                mp = h[key]
                st.metric(label, f"{100 * mp.estimate:+.1f} pp")
                st.caption(f"p = {mp.p_two_sided:.3f}")
        st.write(TEXT["headline"]["hot_hand"])
        st.plotly_chart(forest(data["explorer"]), width="stretch")
        st.caption(TEXT["headline"]["forest_caption"])
        source("results_core.csv", "dashboard/explorer.csv")

    with tabs[1]:
        ex = data["explorer"]
        st.subheader(TEXT["explorer"]["question"])
        st.caption(TEXT["explorer"]["help"])
        group = st.selectbox("Group", ex.group.unique(), key="explorer_group")
        outcome = st.selectbox("Outcome", ex.outcome_label.unique(), key="explorer_outcome")
        row = ex[(ex.group == group) & (ex.outcome_label == outcome)].iloc[0]
        if row.status != "estimated":
            st.warning("Too few shots to estimate.")
        else:
            unit = "ft" if row.outcome == "distance_vs_baseline_ft" else "pp"
            st.metric("Shift (after a make minus after a miss)", f"{row.estimate:+.2f} {unit}",
                      help=f"95% CI {row.ci_low:+.2f} to {row.ci_high:+.2f} {unit}")
            st.write(f"95% interval {row.ci_low:+.2f} to {row.ci_high:+.2f} {unit} · "
                     f"{int(row.n_pairs):,} pairs · {int(row.n_players):,} players")
            st.plotly_chart(explorer_chart(row, unit), width="stretch")
        source("dashboard/explorer.csv")

    with tabs[2]:
        sm = data["shotmap"]
        st.subheader(TEXT["shotmap"]["question"])
        st.caption(TEXT["shotmap"]["help"])
        group = st.selectbox("Group", sm.group.unique(), key="shotmap_group")
        unit = st.radio("Units", ["ft", "m"], horizontal=True, key="shotmap_units")  # D-054
        if unit == "m":
            st.caption("Squares are 0.61 × 0.61 m (2 × 2 ft); 1 ft = 0.3048 m.")
        st.plotly_chart(shot_map(sm, group, unit), width="stretch")
        g = sm[sm.group == group]
        st.write(f"{int(g.shots_after_make.sum()):,} next shots after a make, "
                 f"{int(g.shots_after_miss.sum()):,} after a miss (court bins with 50+ shots).")
        source("dashboard/shotmap.csv")

    with tabs[3]:
        pl, ex = data["players"], data["explorer"]
        st.subheader(TEXT["players"]["question"])
        st.warning(TEXT["players"]["warning"])
        options = [f"{p} · {s}" for p, s in zip(pl.player, pl.season)]  # alphabetical, no ranking
        pick = st.selectbox("Player-season", options, key="player_pick")
        r = pl.iloc[options.index(pick)]
        st.write(f"**{r.player}, {r.season}**: shift {r.shift_ft:+.2f} ft "
                 f"(95% CI {r.ci_low:+.2f} to {r.ci_high:+.2f}; "
                 f"{int(r.pairs_after_make)} pairs after a make, {int(r.pairs_after_miss)} after a miss)")
        tier = {"low": "Low usage", "mid": "Mid usage", "high": "High usage"}.get(r.usage_tier)
        cl = {"rim_bigs": "Rim bigs", "rim_and_corner": "Rim and corner",
              "mid_range_scorers": "Mid-range scorers",
              "three_point_shooters": "Three-point shooters"}.get(r.cluster)
        comp = [("This player-season", r.shift_ft, r.ci_low, r.ci_high)]
        for g in [tier, cl, "All players"]:
            if g:
                e = ex[(ex.group == g) & (ex.outcome == "distance_vs_baseline_ft")].iloc[0]
                comp.append((g, e.estimate, e.ci_low, e.ci_high))
        c = pd.DataFrame(comp, columns=["who", "est", "lo", "hi"]).iloc[::-1]
        fig = go.Figure(go.Scatter(
            x=c.est, y=c.who, mode="markers", marker=dict(color=MAKE, size=9),
            error_x=dict(type="data", symmetric=False, array=c.hi - c.est,
                         arrayminus=c.est - c.lo, color=MAKE)))
        fig.add_vline(x=0, line_color="#999")
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=40),
                          xaxis_title="Shift in next-shot distance (ft, 95% CI)")
        st.plotly_chart(fig, width="stretch")
        st.caption("Player-seasons with at least 100 pairs after a make and 100 after a miss. "
                   "Player estimate: simple difference without controls; group estimates: Model 3.")
        source("dashboard/players.csv", "dashboard/explorer.csv")

    with tabs[4]:
        m = TEXT["method"]
        for key, title in [("summary", "Method"), ("streak_bias", "The streak bias"),
                           ("robustness", "Robustness"), ("limitations", "Limitations"),
                           ("data_credit", "Data")]:
            st.markdown(f"**{title}.** {m[key]}")

    with tabs[5]:
        st.write(TEXT["downloads"]["intro"])
        for name in ["results_core.csv", "results_segments.csv", "results_robustness.csv",
                     "dashboard/explorer.csv", "dashboard/shotmap.csv", "dashboard/players.csv"]:
            st.download_button(name, (PROCESSED / name).read_bytes(), file_name=Path(name).name,
                               mime="text/csv", key=f"dl_{name}")


main()
