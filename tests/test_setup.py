from hothand.config import ROOT, load_config


def test_config_loads_and_has_core_keys():
    cfg = load_config()
    for key in ["random_seed", "data", "pairs", "segments", "split", "inference", "robustness"]:
        assert key in cfg


def test_season_window_is_eight_seasons():
    assert len(load_config()["data"]["seasons"]) == 8


def test_hypotheses_file_exists():
    assert (ROOT / "docs" / "hypotheses.md").exists()
