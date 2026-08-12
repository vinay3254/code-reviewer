import pytest
from pathlib import Path
from roles.verifier import Verifier
from sandbox.docker_runner import SandboxResult

@pytest.fixture
def verifier():
    return Verifier(mock=True)

def test_empty_diff_rejected(verifier):
    res = SandboxResult(exit_code=0, stdout="pass", stderr="")
    result = verifier.verify_stage_a("", res, {})
    assert result.verdict == "rejected"
    assert result.reason == "no_functional_change"

def test_test_file_modification_rejected(verifier):
    diff = "--- a/config.py\n+++ b/config.py\n@@ -1 +1 @@\n+x=1"
    res = SandboxResult(
        exit_code=0,
        stdout="pass",
        stderr="",
        post_test_hashes={"test_config.py": "modified_hash_123"}
    )
    frozen_hashes = {"test_config.py": "original_hash_456"}
    result = verifier.verify_stage_a(diff, res, frozen_hashes)
    assert result.verdict == "rejected"
    assert result.reason == "test_file_modified"

def test_skip_marker_rejected(verifier):
    diff = "--- a/test_config.py\n+++ b/test_config.py\n@@ -1 +1 @@\n+@pytest.mark.skip\n def test_fn(): pass"
    res = SandboxResult(exit_code=0, stdout="pass", stderr="")
    result = verifier.verify_stage_a(diff, res, {})
    assert result.verdict == "rejected"
    assert result.reason == "test_disabled_via_marker"

def test_assertion_suppressed_rejected(verifier):
    diff = "--- a/test_config.py\n+++ b/test_config.py\n@@ -1 +1 @@\n+assert True # noqa"
    res = SandboxResult(exit_code=0, stdout="pass", stderr="")
    result = verifier.verify_stage_a(diff, res, {})
    assert result.verdict == "rejected"
    assert result.reason == "assertion_suppressed"

def test_stage_a_success(verifier):
    diff = "--- a/config.py\n+++ b/config.py\n@@ -1 +1 @@\n+return cfg.get('timeout', 30)"
    res = SandboxResult(
        exit_code=0,
        stdout="pass",
        stderr="",
        post_test_hashes={"test_config.py": "hash_123"}
    )
    frozen_hashes = {"test_config.py": "hash_123"}
    result = verifier.verify_stage_a(diff, res, frozen_hashes)
    assert result.verdict == "accepted"
