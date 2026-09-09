import pytest
from harness.batfish_runner import batfish_available, differential_reachable_pairs

pytestmark = pytest.mark.skipif(not batfish_available(),
                                reason="Batfish service not reachable on localhost:9997")


def test_differential_returns_a_set(tmp_path):
    # Identical before/after snapshots must yield an empty differential set.
    # Batfish requires the snapshot dir to be the parent that contains the
    # aws_configs/ subfolder, not aws_configs/ itself.
    import shutil
    src = "tests/fixtures/aws/hybrid-cloud"
    shutil.copytree(src, tmp_path / "after")
    out = differential_reachable_pairs(src, str(tmp_path / "after"))
    assert isinstance(out, set) and out == set()
