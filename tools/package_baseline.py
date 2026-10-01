"""Compile the baseline with the official harness, then create its submission zip.

Run in the Linux harness environment. This performs no model requests and does
not submit anything to Kaggle. Install the official harness wheels first.
"""

from pathlib import Path
import hashlib
import json
import zipfile


def main() -> None:
    from adk_submission import compile_submission
    from swegemma.config import build_submission_limits
    from swegemma.context import SwegemmaContext
    from swegemma.models import setup_gemma_model_registry

    root = Path(__file__).resolve().parents[1]
    submission = root / "submission"
    limits, constraints = build_submission_limits()
    context = SwegemmaContext()
    models = setup_gemma_model_registry(
        api_base="http://127.0.0.1:8000/v1", api_key="EMPTY", num_retries=0
    )
    agent = compile_submission(
        submission_dir=submission,
        tool_registry=context.create_tools(),
        model_registry=models,
        limits=limits,
        generation_constraints=constraints,
    )
    expected_model = "openai/gemma-4-31b-it-qat-w4a16-ct"
    if agent.model.model != expected_model:
        raise ValueError("Baseline compiled to an unexpected model")
    files = ["agent.yaml", "eval_config.yaml", "prompts/system.md"]
    output = root / "dist" / "submission.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (submission / name).read_bytes())
    print(json.dumps({
        "status": "compiled_and_packaged",
        "model": agent.model.model,
        "agent": agent.name,
        "tools": len(agent.tools),
        "archive": str(output),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "inference_executed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
