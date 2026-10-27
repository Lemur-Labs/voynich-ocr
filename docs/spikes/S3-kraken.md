# S3: Kraken 7.1.1 as a per-glyph-confidence recognizer

## Verdict
Yes, with caveats. Kraken is a CTC (VGSL conv+LSTM) line recognizer, Apache-2.0, trains from scratch on an arbitrary charset. The full per-frame posterior (C x W softmax) is obtainable via `return_logits=True` (baseline lines). The built-in per-char `confidences` is only the max frame prob inside the winning label's span. It is greedy-decode, peaky CTC, and uncalibrated. For "confidence as measured quantity", use the full posteriors and own calibration. Hard constraint: 7.1.1 needs Python <3.14, so laptop 3.14 cannot run it. Use 3.12/3.13 (uv venv or GCP VM).

## Evidence
- PyPI metadata (pypi.org/pypi/kraken/7.1.1/json): requires_python `<3.14,>=3.10`; classifiers 3.10-3.13; Apache-2.0; torch `>=2.9,<=2.14`, lightning==2.6.1.
- `uv pip install --dry-run kraken==7.1.1` in 3.12 venv (scratchpad/s3-venv): resolves 72 pkgs (torch 2.14.0, numpy 2.4.6, scipy 1.15.3, scikit-image 0.25.2). Also run with `--python-version 3.14`; the output I saw was truncated (head/tail only) and I did not confirm the failure message. The metadata bound is the evidence.
- Source (tag 7.1.1, cloned at scratchpad/k; github.com/mittagessen/kraken): 
  - `kraken/lib/ctc_decoder.py` `greedy_decoder`: per label run returns (class, start, end, max prob over the run's frames). That max is the "confidence".
  - `kraken/models/ctc.py` (~L140-235): builds `cuts`/`confidences`; `probs = (logits/temperature).softmax(1)`, `self.outputs` (C,W).
  - `kraken/containers.py` `ocr_record`, `BaselineOCRRecord`, `BBoxOCRRecord`: `.prediction`, `.cuts` (polygons per code point), `.confidences`, `.logits`, `.image`.
  - `kraken/configs/base.py` L196-229: `RecognitionInferenceConfig(temperature=1.0, return_logits=False, ...)`.
  - `kraken/tasks/recognition.py`: `RecognitionTaskModel.load_model(path)`, `.predict(im, segmentation, config)` yields records.
  - `kraken/ketos/recognition.py` (train opts), `kraken/ketos/__init__.py` (global opts), `kraken/ketos/util.py::to_ptl_device`, `kraken/lib/codec.py` (`PytorchCodec`, `merge`, `add_labels`).
- Docs: kraken.re 7.x; in-repo `docs/user_guide/training_recognition.rst`, `inference.rst`, `docs/introduction_to_atr.rst`.
- party: github.com/mittagessen/party, "Page-wise text recognition with lower-supervision line data models", Apache-2.0, active (pushed 2026-09-07).

## Facts the plan needs
- Python: 3.12 recommended (3.10-3.13 OK; 3.14 not). Install: `uv venv --python 3.12 .venv && uv pip install kraken==7.1.1` (pulls torch; on GCP L4 use the CUDA wheel, torch default Linux wheel is CUDA).
- Posteriors: set `RecognitionInferenceConfig(return_logits=True)`. Baseline-line path stores `self.outputs[idx, ..., :olen]`, a (C,W) softmax tensor (temperature already applied; name "logits" is misleading; C includes blank at index 0). Frame-to-glyph spans come from `cuts`. Needs a Segmentation with baselines (blla) or hand-built bbox lines.
  - Quirk: the bbox-line path (`BBoxOCRRecord`) stores `pred`, the decoded tuples, not the tensor. Use baseline lines, or patch/call `TorchSeqRecognizer`-style forward yourself.
  - Full posterior per character = take softmax columns across the glyph span. Do not trust max alone. Code-to-label map: `codec.c2l`.
- GT formats (`ketos train -f`): `path` (line image + `.gt.txt` sidecar, the default), `xml` (auto-detect), `alto`, `page`, `binary` (Arrow dataset from `ketos compile`). Manifest files via `-t`/`-e`. `--linetype baselines|bbox`.
- Charset/codec: built from training data; `-c` custom codec; `--resize union|new|fail` for fine-tune with `--load`. 30-235 symbols is fine. Multi-codepoint labels are supported but cuts are noted as inexact (XXX in ctc.py).
- Validation: `-e` explicit eval set (recommended; better for comparability) or `-p` partition (default 0.9, random split, changes between runs).
- Determinism: global `ketos -s SEED -r train ...` (`-r` defaults seed to 42, uses lightning `seed_everything(workers=True)`). Global opts go before `train`: `-d cuda:0|cpu|mps`, `--precision`, `--workers`.
- Training opts: `--spec`/`--variant tiny|small|medium`, `--height` (96 default), `--max-width` (2560), `-B`, `-q early --lag N --min-epochs N`, `--schedule`, `--warmup`, `--augment`.
- Compute: CPU, CUDA, and Apple MPS are supported (`to_ptl_device`, docs inference.rst L189-190). `kraken ... --temperature F` is the CLI softmax temperature.
- Data minimum: docs (introduction_to_atr.rst) say a single clean uniform hand with a small alphabet needs "a couple of dozen pages". No line-count figure is given. 5,000 lines is comfortably above that.
- GPU-hour estimate: ~0.5-2 L4-hours for 5,000 lines to convergence (small VGSL, ~50-150 epochs with early stopping, ~10-40 s/epoch on an L4 at fp16/bf16). Basis: my own order-of-magnitude reasoning from the model size and typical kraken experience; no timing figure is published in the 7.1.1 docs/source I read. Budget 2-4 h to allow for hyperparameter and seed repeats. Do not cite it as measured.
- Segmentation: blla default model ships in the wheel (`kraken/blla.mlmodel`; loaded when no path is given in `kraken/tasks/segmentation.py` L124-131). It is trained on other scripts, so Voynich line detection may need checking. Pre-segmented lines avoid it.
- party: page-level recognizer (Apache-2.0), separate from kraken's CTC. I did not verify whether it exposes per-character confidences or is usable on an unknown script (it is described as pretrained, "lower-supervision"). Not suitable by default; the CTC route is the documented one.
- Calibration: kraken has only the global `temperature` knob (no fitting or ECE tooling) in the source/docs I searched (grep of docs: no "calibrat"). Literature knowledge (not retrieved this session): CTC models are known to be overconfident and peaky (Graves 2006 behaviour; Guo et al. 2017 temperature scaling is the standard fix). Fit T on held-out lines by NLL/ECE.

## Unverified
- Exact 3.14 failure output from uv; actual training wall time (no run done); L4 throughput.
- Whether CTC "confidence" differs in baseline vs bbox records beyond the logits quirk; whether `return_logits` is exposed via the `kraken` CLI (only the Python config confirmed).
- party's confidence output, license of pretrained weights, and fit for unknown scripts.
- Literature citations on CTC calibration were not fetched; named from memory.
- docs on kraken.re were read via the repo's `docs/` at tag 7.1.1, not the rendered site.
