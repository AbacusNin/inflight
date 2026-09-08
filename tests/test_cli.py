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
