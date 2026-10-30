from pathlib import Path

import pytest

from spectral_audit.config import load_demo_config
from spectral_audit.types import Band, DemoConfig, RecordConfig, ToneSignalConfig


def test_supplied_config():
    config = load_demo_config(Path("configs/m0_tones.toml"))
    assert config.record.n_samples == 256
    assert [b.name for b in config.bands] == ["low", "mid", "high"]


@pytest.mark.parametrize(
    "before,after",
    [
        ("schema_version = 1", "schema_version = 2"),
        ("n_samples = 256", "n_samples = true"),
        ("sampling_rate_hz = 128.0", "sampling_rate_hz = 0.0"),
        ('mean_policy = "none"', 'mean_policy = "demean"'),
        ('kind = "tones"', 'kind = "noise"'),
        ("frequencies_hz = [8.0, 24.0]", "frequencies_hz = [8.0]"),
        ("amplitudes = [1.0, 0.5]", "amplitudes = [1.0, nan]"),
        ("upper_hz = 16.0", "upper_hz = 17.0"),
        ("upper_hz = 64.0", "upper_hz = 65.0"),
        ("experiment_id =", "unexpected = 2\nexperiment_id ="),
        ('fft_norm = "ortho"', 'fft_norm = "backward"'),
    ],
)
def test_invalid_config(tmp_path, before, after):
    content = Path("configs/m0_tones.toml").read_text(encoding="utf-8")
    path = tmp_path / "bad.toml"
    path.write_text(content.replace(before, after), encoding="utf-8")
    with pytest.raises((ValueError, __import__("tomllib").TOMLDecodeError)):
        load_demo_config(path)


def test_band_validation():
    r = RecordConfig(8, 8, "V")
    s = ToneSignalConfig((1,), (1,), (0,))
    for bands in [
        (Band("a", 0, 2), Band("a", 2, 4, True)),
        (Band("a", 0, 2), Band("b", 1, 4, True)),
        (Band("a", 0, 2), Band("b", 3, 4, True)),
        (Band("a", 0, 2, True), Band("b", 2, 4, True)),
    ]:
        with pytest.raises(ValueError):
            DemoConfig("bad", r, s, bands)
