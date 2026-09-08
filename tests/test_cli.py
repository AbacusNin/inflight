import json

import pytest

from inflight.gate.cli import main


def test_cli_blocks_sole_path(capsys):
    code = main(["evaluate",
                 "--snapshot", "tests/fixtures/trap_sole_path.json",
                 "--change", "tests/fixtures/change_remove_r1.json"])
    out = capsys.readouterr().out
    assert code == 3
    assert "block" in out


def test_cli_safe_on_redundant(capsys):
    code = main(["evaluate",
                 "--snapshot", "tests/fixtures/trap_redundant_path.json",
                 "--change", "tests/fixtures/change_remove_r1.json"])
    assert code == 0


def test_cli_malformed_change_fails_closed(tmp_path):
    bad = tmp_path / "bad_change.json"
    bad.write_text(json.dumps({"kind": "remove_sg_rules", "rule_ids": None}))
    code = main(["evaluate",
                 "--snapshot", "tests/fixtures/trap_sole_path.json",
                 "--change", str(bad)])
    assert code == 3


def test_cli_usage_error_exits_1():
    with pytest.raises(SystemExit) as exc:
        main(["evaluate", "--snapshot", "tests/fixtures/trap_sole_path.json"])
    assert exc.value.code == 1
