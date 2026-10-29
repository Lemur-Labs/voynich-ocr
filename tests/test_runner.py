import pytest

from voynich_ocr import runner


def test_gate_training_stops_early_and_reads_lines_as_baselines():
    args = runner.ketos_args(20261027, runner.MODELS / "x")
    assert args[args.index("--linetype") + 1] == "baselines"
    assert args[args.index("-q") + 1] == "early"
    assert args[args.index("-t") + 1] == str(runner.LINES / "train.txt")
    assert args[args.index("--lrate") + 1] == "1e-4"
    assert args[args.index("--warmup") + 1] == "1000"


def test_arm_runs_a_fixed_number_of_epochs_on_its_own_dataset_with_its_own_args():
    args = runner.ketos_args(20261027, runner.MODELS / "x", "lr-paper")
    assert args[args.index("-q") + 1 : args.index("-q") + 4] == ["fixed", "-N", str(runner.ARM_EPOCHS)]
    assert args[args.index("-t") + 1] == str(runner.PAPER / "train.txt")
    assert args[args.index("--lrate") + 1] == "1e-4"
    assert args.index("train") < args.index("--lrate") < args.index("-o")


def test_pack_refuses_a_dataset_that_was_never_built(tmp_path):
    with pytest.raises(SystemExit):
        runner.pack([tmp_path / "lines-paper"])


def test_train_takes_one_arm(monkeypatch):
    monkeypatch.setattr(runner, "train", lambda *a: pytest.fail("trained"))
    with pytest.raises(SystemExit):
        runner.main(["train", "--seed", "20261027", "--arm", "lr", "--arm", "paper"])


def test_instance_name_names_its_arms():
    assert runner.instance_name(20261027, "abcdef1234", ["lr", "lr-paper"]) == "train-20261027-abcdef12-lr-lr-paper"
    assert runner.instance_name(20261027, "abcdef1234", []) == "train-20261027-abcdef12"
