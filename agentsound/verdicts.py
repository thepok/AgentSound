"""Engine-owned audio judgments; consumers choose codes and attach remedies."""
import json
import subprocess


DELIVERY = {
    'profile': {'loudnessToleranceLu': 0.05},
    'streaming': {'loudnessToleranceLu': 1.0},
    'endless': {'loudnessToleranceLu': 0.0},
}


def evaluate(report, *, policy=None):
    """Use emitted findings directly, or ask the same C++ evaluator for delivery overrides.

    Partial/old reports are evaluated by the engine too; no Python threshold fallback.
    """
    if policy is None and 'findings' in report:
        return report['findings']
    from .cli import find_engine
    proc = subprocess.run([str(find_engine()), 'verdicts'],
                          input=json.dumps({'report': report, 'policy': policy or {}}),
                          capture_output=True, text=True, encoding='utf-8')
    if proc.returncode:
        raise ValueError(f"engine verdicts: {proc.stderr.strip()}")
    return json.loads(proc.stdout)
