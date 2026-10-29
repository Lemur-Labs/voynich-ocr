from voynich_ocr import runner


def test_gate_training_stops_early_and_reads_lines_as_baselines():
    args = runner.ketos_args(20261027, runner.MODELS / "x")
    assert args[args.index("--linetype") + 1] == "baselines"
    assert args[args.index("-q") + 1] == "early"
    assert args[args.index("-t") + 1] == str(runner.LINES / "train.txt")


def test_arm_runs_a_fixed_number_of_epochs_on_its_own_dataset_with_its_own_args():
    args = runner.ketos_args(20261027, runner.MODELS / "x", "lr-paper")
    assert args[args.index("-q") + 1 : args.index("-q") + 4] == ["fixed", "-N", str(runner.ARM_EPOCHS)]
    assert args[args.index("-t") + 1] == str(runner.PAPER / "train.txt")
    assert args[args.index("--lrate") + 1] == "1e-4"
    assert args.index("train") < args.index("--lrate") < args.index("-o")
