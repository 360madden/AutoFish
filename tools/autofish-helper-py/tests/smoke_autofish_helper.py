from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER_PATH = REPO_ROOT / "tools" / "autofish-helper-py" / "autofish_helper.py"
DOC_VALIDATOR_PATH = REPO_ROOT / "tools" / "autofish-helper-py" / "tests" / "validate_doc_commands.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("autofish_helper", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper module from {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_doc_validator():
    spec = importlib.util.spec_from_file_location("validate_doc_commands", DOC_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load doc command validator from {DOC_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_helper_commands_valid(doc_validator, label: str, markdown: str) -> None:
    failures = doc_validator.validate_markdown_text(label, markdown)
    assert not failures, "\n".join(failures)


def test_doc_command_validator_surface(helper, doc_validator) -> None:
    surface = doc_validator.build_command_surface(helper)
    assert "target-snapshot" in surface
    assert "doctor" in surface
    assert "session-plan" in surface
    assert "signal-proof" in surface
    assert "checklist" in surface["session-plan"]
    assert "doctor" in surface["session-plan"]
    assert "stop-file" in surface["session-plan"]
    assert "clear" in surface["session-plan"]["stop-file"]
    assert "one-cast" in surface["signal-proof"]
    assert "bounded-session" in surface["signal-proof"]
    assert "facing-delta" in surface["signal-proof"]
    assert "facing-from-coords" in surface["signal-proof"]
    assert "doctor" in surface["signal-proof"]


def test_profile_defaults(helper) -> None:
    args = argparse.Namespace(
        profile="starter-pond",
        profile_root="profiles",
        key=None,
        pull_clicks=None,
        cast_wait_seconds=None,
        post_pull_delay_ms=None,
        crop_size=None,
        key_hold_ms=None,
        post_hover_delay_ms=None,
        post_key_delay_ms=None,
        post_click_delay_ms=None,
        max_casts=None,
        max_allowed_casts=None,
        inter_cast_delay_ms=None,
    )
    info = helper.apply_fishing_runtime_defaults(args, include_session_defaults=True)
    assert info["profile"]["id"] == "starter-pond"
    assert args.key == "8"
    assert args.cast_wait_seconds == 12.0
    assert args.post_pull_delay_ms == 2200
    assert args.max_casts == 3
    assert args.max_allowed_casts == 10


def test_session_plan_defaults(helper) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-smoke-") as tmp:
        plan_path = Path(tmp) / "session-plan.json"
        plan = {
            "schema": "autofish.sessionPlan.v1",
            "generatedAtUtc": "2026-05-26T00:00:00+00:00",
            "target": {"pid": 1234, "hwnd": "0x1234"},
            "fishablePoint": {"x": 100, "y": 200, "coordinateSpace": "client"},
            "profile": {"id": "starter-pond", "root": "profiles"},
            "defaults": {"key": "8", "maxCasts": 3, "pullClicks": 1},
            "safety": {"requiresExactPidHwnd": True, "noMovement": True},
        }
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        args = argparse.Namespace(
            session_plan=str(plan_path),
            pid=None,
            hwnd=None,
            x=None,
            y=None,
            profile=None,
            profile_root="profiles",
            key=None,
            pull_clicks=None,
            cast_wait_seconds=None,
            post_pull_delay_ms=None,
            stop_file=None,
            max_casts=None,
            max_allowed_casts=None,
            inter_cast_delay_ms=None,
        )
        info = helper.apply_session_plan_defaults(args, include_session_defaults=True)
        assert info["sessionPlan"]["plan"]["schema"] == "autofish.sessionPlan.v1"
        assert args.pid == 1234
        assert args.hwnd == "0x1234"
        assert args.x == 100
        assert args.y == 200
        assert args.profile == "starter-pond"
        assert args.key == "8"
        assert args.max_casts == 3
        assert args.stop_file == ".autofish-live/STOP.txt"


def test_runbook_render(helper, doc_validator) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-runbook-") as tmp:
        plan_path = Path(tmp) / "session-plan.json"
        with contextlib.redirect_stdout(io.StringIO()):
            helper.run_session_plan_create(
                argparse.Namespace(
                    pid=1234,
                    hwnd="0x1234",
                    x=100,
                    y=200,
                    profile="starter-pond",
                    profile_root="profiles",
                    key="8",
                    max_casts=3,
                    max_allowed_casts=10,
                    pull_clicks=1,
                    cast_wait_seconds=None,
                    post_pull_delay_ms=None,
                    inter_cast_delay_ms=800,
                    stop_file=None,
                    validate_target=False,
                    output=str(plan_path),
                )
            )
        markdown = helper.render_session_plan_runbook(str(plan_path), ".autofish-live")
        assert_helper_commands_valid(doc_validator, "generated-session-plan-runbook", markdown)
        assert "signal-proof one-cast --session-plan" in markdown
        assert "signal-proof bounded-session --session-plan" in markdown
        assert "--signal oneCast" in markdown
        assert "session-plan explain" in markdown
        assert "session-plan preflight" in markdown
        checklist = helper.render_session_plan_checklist(str(plan_path), ".autofish-live", ".autofish-live/signal-proof-decisions.json")
        assert_helper_commands_valid(doc_validator, "generated-session-plan-checklist", checklist)
        assert "AutoFish Session Plan Checklist" in checklist
        assert "target-snapshot" in checklist
        assert "ready-one-cast" in checklist
        assert "signal-proof bounded-session --session-plan" in checklist
        assert "session-plan stop-file create" in markdown
        assert "session-plan stop-file clear" in markdown
        assert ".autofish-live/STOP.txt" in markdown
        assert "No command in this runbook sends movement" in markdown


def test_session_plan_doctor_report(helper, doc_validator) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-session-doctor-") as tmp:
        plan_path = Path(tmp) / "session-plan.json"
        with contextlib.redirect_stdout(io.StringIO()):
            helper.run_session_plan_create(
                argparse.Namespace(
                    pid=1234,
                    hwnd="0x1234",
                    x=100,
                    y=200,
                    profile="starter-pond",
                    profile_root="profiles",
                    key="8",
                    max_casts=3,
                    max_allowed_casts=10,
                    pull_clicks=1,
                    cast_wait_seconds=None,
                    post_pull_delay_ms=None,
                    inter_cast_delay_ms=800,
                    stop_file=None,
                    validate_target=False,
                    output=str(plan_path),
                )
            )
        decision_register = Path(tmp) / "decisions.json"
        report = helper.build_session_plan_doctor_report(
            str(plan_path),
            str(decision_register),
            ".autofish-live",
            max_plan_age_minutes=0,
        )
        assert report["schema"] == "autofish.sessionPlan.doctor.v1"
        assert not report["sendsGameInput"]
        assert report["summary"]["gateCount"] >= 1
        assert "gateReport" in report
        assert "checklistMarkdown" in report
        assert "nextAction" in report
        markdown = helper.render_session_plan_doctor_markdown(report)
        assert "AutoFish Session Plan Doctor" in markdown
        assert "Gate table" in markdown
        assert "Checklist" in markdown
        assert_helper_commands_valid(doc_validator, "generated-session-plan-doctor", markdown)

        output_root = Path(tmp) / "doctor-out"
        with contextlib.redirect_stdout(io.StringIO()) as doctor_output:
            assert (
                helper.run_session_plan_doctor(
                    argparse.Namespace(
                        path=str(plan_path),
                        proof_root=".autofish-live",
                        decision_register=str(decision_register),
                        max_plan_age_minutes=0,
                        output_root=str(output_root),
                    )
                )
                == 0
            )
        result = json.loads(doctor_output.getvalue())
        assert Path(result["doctor"]).exists()
        assert Path(result["markdown"]).exists()


def test_autofish_doctor_bundle(helper, doc_validator) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-autofish-doctor-") as tmp:
        proof_root = Path(tmp) / "proofs"
        proof_root.mkdir()
        plan_path = Path(tmp) / "session-plan.json"
        with contextlib.redirect_stdout(io.StringIO()):
            helper.run_session_plan_create(
                argparse.Namespace(
                    pid=1234,
                    hwnd="0x1234",
                    x=100,
                    y=200,
                    profile="starter-pond",
                    profile_root="profiles",
                    key="8",
                    max_casts=3,
                    max_allowed_casts=10,
                    pull_clicks=1,
                    cast_wait_seconds=None,
                    post_pull_delay_ms=None,
                    inter_cast_delay_ms=800,
                    stop_file=None,
                    validate_target=False,
                    output=str(plan_path),
                )
            )
        decision_register = Path(tmp) / "decisions.json"
        report = helper.build_autofish_doctor_report(
            str(proof_root),
            str(decision_register),
            str(plan_path),
            max_plan_age_minutes=0,
        )
        assert report["schema"] == "autofish.doctor.v1"
        assert not report["sendsGameInput"]
        assert report["summary"]["sessionPlanExists"]
        assert report["summary"]["sessionPlanLoaded"]
        assert report["signalProofDoctor"]["schema"] == "autofish.signalProof.doctor.v1"
        assert report["sessionPlanDoctor"]["schema"] == "autofish.sessionPlan.doctor.v1"
        assert report["nextAction"]
        markdown = helper.render_autofish_doctor_markdown(report)
        assert "AutoFish Doctor" in markdown
        assert "Signal proof doctor" in markdown
        assert "Session plan doctor" in markdown
        assert "fail-closed status: passed" in markdown
        assert_helper_commands_valid(doc_validator, "generated-autofish-doctor", markdown)

        missing_report = helper.build_autofish_doctor_report(
            str(proof_root),
            str(decision_register),
            str(Path(tmp) / "missing-session-plan.json"),
            max_plan_age_minutes=0,
            fail_on=["missing-session-plan"],
        )
        assert not missing_report["summary"]["sessionPlanExists"]
        assert missing_report["sessionPlanDoctor"] is None
        assert missing_report["failed"]
        assert missing_report["failures"][0]["rule"] == "missing-session-plan"
        assert "Create a session plan" in " ".join(missing_report["nextActions"])

        output_root = Path(tmp) / "doctor-out"
        with contextlib.redirect_stdout(io.StringIO()) as doctor_output:
            assert (
                helper.run_autofish_doctor(
                    argparse.Namespace(
                        proof_root=str(proof_root),
                        decision_register=str(decision_register),
                        session_plan=str(plan_path),
                        max_plan_age_minutes=0,
                        fail_on=[],
                        refresh_summary=True,
                        output_root=str(output_root),
                    )
                )
                == 0
            )
        result = json.loads(doctor_output.getvalue())
        assert Path(result["doctor"]).exists()
        assert Path(result["markdown"]).exists()
        assert result["nextAction"]
        assert Path(result["summaryArtifacts"]["summary"]).exists()
        assert Path(result["summaryArtifacts"]["markdown"]).exists()
        persisted_doctor = json.loads((output_root / "doctor.json").read_text(encoding="utf-8"))
        assert persisted_doctor["summaryArtifacts"] == result["summaryArtifacts"]
        assert "Refreshed signal-proof summary artifacts" in (output_root / "doctor.md").read_text(encoding="utf-8")

        fail_output_root = Path(tmp) / "doctor-fail-out"
        with contextlib.redirect_stdout(io.StringIO()) as fail_output:
            assert (
                helper.run_autofish_doctor(
                    argparse.Namespace(
                        proof_root=str(proof_root),
                        decision_register=str(decision_register),
                        session_plan=str(Path(tmp) / "missing-session-plan.json"),
                        max_plan_age_minutes=0,
                        fail_on=["missing-session-plan"],
                        output_root=str(fail_output_root),
                    )
                )
                == 1
            )
        fail_result = json.loads(fail_output.getvalue())
        assert not fail_result["ok"]
        assert fail_result["failed"]
        assert fail_result["failures"][0]["rule"] == "missing-session-plan"
        assert Path(fail_result["doctor"]).exists()

        next_action_output_root = Path(tmp) / "doctor-next-action-out"
        with contextlib.redirect_stdout(io.StringIO()) as next_action_output:
            assert (
                helper.run_autofish_doctor(
                    argparse.Namespace(
                        proof_root=str(proof_root),
                        decision_register=str(decision_register),
                        session_plan=str(Path(tmp) / "missing-session-plan.json"),
                        max_plan_age_minutes=0,
                        fail_on=[],
                        next_action_only=True,
                        refresh_summary=True,
                        output_root=str(next_action_output_root),
                    )
                )
                == 0
            )
        next_action_text = next_action_output.getvalue().strip()
        assert next_action_text
        assert "{" not in next_action_text
        assert (next_action_output_root / "doctor.json").exists()
        assert (next_action_output_root / "signal-proof-summary" / "summary.json").exists()


def test_direct_live_command_stop_file_defaults(helper) -> None:
    parser = helper.build_parser()
    one_cast = parser.parse_args(
        [
            "signal-proof",
            "one-cast",
            "--pid",
            "1234",
            "--hwnd",
            "0x1234",
            "--x",
            "100",
            "--y",
            "200",
            "--dry-run",
        ]
    )
    assert one_cast.stop_file == helper.DEFAULT_STOP_FILE
    assert one_cast.max_plan_age_minutes == helper.DEFAULT_SESSION_PLAN_MAX_AGE_MINUTES

    bounded_session = parser.parse_args(
        [
            "signal-proof",
            "bounded-session",
            "--pid",
            "1234",
            "--hwnd",
            "0x1234",
            "--x",
            "100",
            "--y",
            "200",
            "--dry-run",
        ]
    )
    assert bounded_session.stop_file == helper.DEFAULT_STOP_FILE
    assert bounded_session.max_plan_age_minutes == helper.DEFAULT_SESSION_PLAN_MAX_AGE_MINUTES


def test_red_reticle_click_guard(helper) -> None:
    red_capture = {
        "colorStats": {
            "suggestedReticleColor": "red",
            "legacySuggestedReticleColor": "red",
            "suggestionReason": "red_orange_pixels_met_invalid_reticle_threshold",
        }
    }
    blocked = helper.build_red_reticle_click_guard(
        red_capture,
        click_planned=True,
        allow_red_reticle_click=False,
    )
    assert blocked["required"]
    assert not blocked["passed"]
    assert "refusing" in blocked["reason"]

    overridden = helper.build_red_reticle_click_guard(
        red_capture,
        click_planned=True,
        allow_red_reticle_click=True,
    )
    assert overridden["passed"]
    assert overridden["overridden"]

    skipped = helper.build_red_reticle_click_guard(
        red_capture,
        click_planned=False,
        allow_red_reticle_click=False,
    )
    assert not skipped["required"]
    assert skipped["passed"]

    yellow = helper.build_red_reticle_click_guard(
        {"colorStats": {"suggestedReticleColor": "yellow"}},
        click_planned=True,
        allow_red_reticle_click=False,
    )
    assert yellow["passed"]


def test_red_reticle_guard_summary(helper) -> None:
    manifest_path = Path("one-cast-red-reticle") / "manifest.json"
    manifest = {
        "schema": "autofish.signalProof.oneCast.v1",
        "generatedAtUtc": "2026-05-26T00:00:00+00:00",
        "mode": "confirm-input",
        "error": "Red reticle was detected after the fishing key; refusing the confirm click.",
        "actions": [{"name": "abort-confirm-click"}],
        "captures": [{"label": "after-key"}],
        "request": {"pullClicks": 1, "castWaitSeconds": 18},
        "safety": {"clickCount": 0},
        "result": {"classification": "unproven", "completed": False, "liveInputSent": True},
        "decision": {"classification": "evidence-only"},
        "reviewGates": {
            "redReticleClickGuard": {
                "required": True,
                "passed": False,
                "suggestedReticleColor": "red",
                "reason": "Red reticle was detected after the fishing key; refusing the confirm click.",
            }
        },
    }
    summary = helper.summarize_signal_proof_manifest(manifest_path, manifest)
    assert summary["suggestedReview"] == "blocked-red-reticle-review"
    assert "redReticleClickGuard" in summary["failedReviewGateNames"]
    assert summary["redReticleClickGuardCount"] == 1
    assert summary["redReticleClickGuardFailedCount"] == 1
    assert summary["redReticleClickGuardRedCount"] == 1

    markdown = helper.render_signal_proof_markdown(
        {
            "generatedAtUtc": "2026-05-26T00:00:00+00:00",
            "proofRoot": ".autofish-live",
            "manifestCount": 1,
            "bySignal": {"oneCast": {"count": 1, "suggestedReviews": {summary["suggestedReview"]: 1}}},
            "summaries": [summary],
        }
    )
    assert "red-reticle guard: failed 1/1" in markdown
    assert "review gates failed: redReticleClickGuard" in markdown
    assert "blocked-red-reticle-review" in markdown

    bounded_summary = helper.summarize_signal_proof_manifest(
        Path("bounded-red-reticle") / "manifest.json",
        {
            "schema": "autofish.signalProof.boundedSession.v1",
            "generatedAtUtc": "2026-05-26T00:00:00+00:00",
            "mode": "confirm-input",
            "casts": [
                {
                    "castNumber": 1,
                    "completed": False,
                    "actions": [{"name": "abort-confirm-click"}],
                    "redReticleClickGuard": {
                        "required": True,
                        "passed": False,
                        "suggestedReticleColor": "red",
                        "reason": "Red reticle was detected after the fishing key; refusing the confirm click.",
                    },
                }
            ],
            "captures": [{"label": "cast-001-after-key"}],
            "request": {"maxCasts": 3, "pullClicks": 1, "castWaitSeconds": 18},
            "safety": {"maxClickCount": 0},
            "result": {"classification": "unproven", "completed": False, "liveInputSent": True},
            "decision": {"classification": "evidence-only"},
            "reviewGates": {
                "redReticleClickGuard": {
                    "required": True,
                    "passed": False,
                    "suggestedReticleColor": "red",
                }
            },
        },
    )
    assert bounded_summary["suggestedReview"] == "blocked-red-reticle-review"
    assert bounded_summary["redReticleClickGuardCount"] == 1
    assert bounded_summary["redReticleClickGuardFailedCount"] == 1


def test_manifest_shape_validation_summary(helper) -> None:
    invalid_manifest = {
        "schema": "autofish.signalProof.oneCast.v1",
        "generatedAtUtc": "2026-05-26T00:00:00+00:00",
        "mode": "confirm-input",
        "request": {},
        "safety": {},
        "captures": [],
        "actions": [],
        "result": {},
        "decision": {},
    }
    errors = helper.validate_signal_proof_manifest_shape(invalid_manifest)
    assert "reviewGates is required for oneCast manifests" in errors

    summary = helper.summarize_signal_proof_manifest(Path("invalid-one-cast") / "manifest.json", invalid_manifest)
    assert not summary["manifestShapeValid"]
    assert summary["suggestedReview"] == "invalid-manifest-rerun"

    markdown = helper.render_signal_proof_markdown(
        {
            "generatedAtUtc": "2026-05-26T00:00:00+00:00",
            "proofRoot": ".autofish-live",
            "manifestCount": 1,
            "bySignal": {"oneCast": {"count": 1, "suggestedReviews": {summary["suggestedReview"]: 1}}},
            "summaries": [summary],
        }
    )
    assert "manifest validation errors" in markdown
    assert "reviewGates is required for oneCast manifests" in markdown


def test_signal_proof_doctor_report(helper) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-doctor-") as tmp:
        root = Path(tmp) / "proofs"
        invalid_manifest_path = root / "invalid-one-cast" / "manifest.json"
        invalid_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        invalid_manifest_path.write_text(
            json.dumps(
                {
                    "schema": "autofish.signalProof.oneCast.v1",
                    "generatedAtUtc": "2026-05-26T00:00:00+00:00",
                    "mode": "confirm-input",
                    "request": {},
                    "safety": {},
                    "captures": [],
                    "actions": [],
                    "result": {"completed": False},
                    "decision": {"classification": "evidence-only"},
                }
            ),
            encoding="utf-8",
        )
        register_path = Path(tmp) / "decisions.json"
        register_path.write_text(
            json.dumps(
                {
                    "schema": "autofish.signalProof.decisions.v1",
                    "entries": [
                        {
                            "signal": "oneCast",
                            "decision": "fallback-only",
                            "reason": "Smoke-test decision with missing evidence.",
                            "evidence": ["missing/manifest.json"],
                            "proofRoot": str(root),
                        }
                    ],
                    "latestBySignal": {},
                }
            ),
            encoding="utf-8",
        )

        report = helper.build_signal_proof_doctor_report(str(root), str(register_path))
        assert report["schema"] == "autofish.signalProof.doctor.v1"
        assert not report["sendsGameInput"]
        assert report["summary"]["manifestCount"] == 1
        assert report["summary"]["invalidManifestCount"] == 1
        assert report["summary"]["weakDecisionEvidenceCount"] == 1
        assert report["nextActions"]
        markdown = helper.render_signal_proof_doctor_markdown(report)
        assert "AutoFish Signal Proof Doctor" in markdown
        assert "invalid manifests: 1" in markdown

        output_root = Path(tmp) / "doctor-out"
        with contextlib.redirect_stdout(io.StringIO()) as doctor_output:
            assert (
                helper.run_signal_proof_doctor(
                    argparse.Namespace(
                        proof_root=str(root),
                        decision_register=str(register_path),
                        output_root=str(output_root),
                    )
                )
                == 0
            )
        result = json.loads(doctor_output.getvalue())
        assert Path(result["doctor"]).exists()
        assert Path(result["markdown"]).exists()


def test_facing_delta_manifest_result_is_always_dict(helper) -> None:
    manifest = {
        "schema": "autofish.signalProof.facingDelta.v1",
        "generatedAtUtc": "2026-05-26T00:00:00+00:00",
        "mode": "dry-run",
        "request": {},
        "safety": {"sendsMovement": False},
        "result": helper.build_facing_delta_result(
            "blocked-no-fresh-before-position",
            reason="Fresh ChromaLink before-position is required.",
            before_coordinate_ready=False,
        ),
        "decision": {"classification": "blocked-no-fresh-before-position"},
    }
    assert helper.validate_signal_proof_manifest_shape(manifest) == []
    summary = helper.summarize_signal_proof_manifest(Path("manifest.json"), manifest)
    assert summary["manifestShapeValid"]
    assert summary["classification"] == "blocked-no-fresh-before-position"
    assert summary["suggestedReview"] == "blocked-rerun-prerequisites"

    with tempfile.TemporaryDirectory(prefix="autofish-helper-facing-delta-invalid-") as tmp:
        output_root = Path(tmp) / "facing-delta"
        args = helper.build_parser().parse_args(
            [
                "signal-proof",
                "facing-delta",
                "--pid",
                "1234",
                "--hwnd",
                "0x1",
                "--dry-run",
                "--output-root",
                str(output_root),
            ]
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            assert helper.run_signal_proof_facing_delta(args) == 1
        written = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
        assert isinstance(written["result"], dict)
        assert helper.validate_signal_proof_manifest_shape(written) == []


def test_facing_from_coords_manual_delta(helper) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-facing-from-coords-") as tmp:
        output_root = Path(tmp) / "facing-from-coords"
        with contextlib.redirect_stdout(io.StringIO()) as run_output:
            assert (
                helper.run_signal_proof_facing_from_coords(
                    argparse.Namespace(
                        before_line="coords x=10 y=20 z=5 playerUnit=u1",
                        before_x=None,
                        before_y=None,
                        before_z=None,
                        after_line="coords x=10 y=21 z=5 playerUnit=u1",
                        after_x=None,
                        after_y=None,
                        after_z=None,
                        min_distance=0.01,
                        output_root=str(output_root),
                    )
                )
                == 0
            )
        result = json.loads(run_output.getvalue())
        assert result["ok"]
        assert result["classification"] == "usable-coordinate-delta"
        assert result["operationalFacing"]["isNativeActorFacing"] is False

        manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["schema"] == "autofish.signalProof.facingDelta.v1"
        assert manifest["mode"] == "manual-coordinate-delta"
        assert not manifest["safety"]["sendsInput"]
        assert not manifest["safety"]["sendsMovement"]
        assert manifest["before"]["coordinateReady"]
        assert manifest["after"]["coordinateReady"]
        assert helper.validate_signal_proof_manifest_shape(manifest) == []

        summary = helper.summarize_signal_proof_manifest(output_root / "manifest.json", manifest)
        assert summary["usable"]
        assert summary["suggestedReview"] == "operational-facing-candidate-review"


def test_target_snapshot_invalid_hwnd(helper) -> None:
    parser = helper.build_parser()
    args = parser.parse_args(
        [
            "target-snapshot",
            "--pid",
            "1234",
            "--hwnd",
            "0x1",
            "--require-foreground",
            "--require-readable",
        ]
    )
    report = helper.build_target_snapshot_report(args)
    assert report["schema"] == "autofish.targetSnapshot.v1"
    assert not report["safety"]["sendsInput"]
    assert not report["safety"]["focusesWindow"]
    assert not report["readiness"]["exactTarget"]
    assert not report["readiness"]["targetSnapshotReady"]
    assert report["gates"]["exactTarget"]["required"]
    with contextlib.redirect_stdout(io.StringIO()) as snapshot_output:
        assert helper.run_target_snapshot(args) == 1
    snapshot_report = json.loads(snapshot_output.getvalue())
    assert snapshot_report["schema"] == "autofish.targetSnapshot.v1"
    assert not snapshot_report["readiness"]["targetSnapshotReady"]


def test_stale_session_plan_refuses_plan_backed_proofs(helper) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-stale-plan-") as tmp:
        plan_path = Path(tmp) / "stale-session-plan.json"
        plan = {
            "schema": "autofish.sessionPlan.v1",
            "generatedAtUtc": "2026-05-26T00:00:00+00:00",
            "target": {"pid": 1234, "hwnd": "0x1234"},
            "fishablePoint": {"x": 100, "y": 200, "coordinateSpace": "client"},
            "profile": {"id": "starter-pond", "root": "profiles"},
            "defaults": {"key": "8", "maxCasts": 3, "maxAllowedCasts": 10, "pullClicks": 1},
            "safety": {"requiresExactPidHwnd": True, "noMovement": True},
        }
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        parser = helper.build_parser()
        one_cast = parser.parse_args(
            [
                "signal-proof",
                "one-cast",
                "--session-plan",
                str(plan_path),
                "--dry-run",
                "--max-plan-age-minutes",
                "1",
                "--output-root",
                str(Path(tmp) / "one-cast-out"),
            ]
        )
        with contextlib.redirect_stderr(io.StringIO()) as one_cast_error:
            assert helper.run_signal_proof_one_cast(one_cast) == 1
        assert "too old" in one_cast_error.getvalue()
        one_cast_manifest = json.loads((Path(tmp) / "one-cast-out" / "manifest.json").read_text(encoding="utf-8"))
        assert "reviewGates" in one_cast_manifest
        assert not one_cast_manifest["reviewGates"]["planFresh"]["passed"]
        one_cast_summary = helper.summarize_signal_proof_manifest(
            Path(tmp) / "one-cast-out" / "manifest.json",
            one_cast_manifest,
        )
        assert "planFresh" in one_cast_summary["failedReviewGateNames"]

        bounded_session = parser.parse_args(
            [
                "signal-proof",
                "bounded-session",
                "--session-plan",
                str(plan_path),
                "--dry-run",
                "--max-plan-age-minutes",
                "1",
                "--output-root",
                str(Path(tmp) / "bounded-session-out"),
            ]
        )
        with contextlib.redirect_stderr(io.StringIO()) as bounded_error:
            assert helper.run_signal_proof_bounded_session(bounded_session) == 1
        assert "too old" in bounded_error.getvalue()
        bounded_manifest = json.loads((Path(tmp) / "bounded-session-out" / "manifest.json").read_text(encoding="utf-8"))
        assert "reviewGates" in bounded_manifest
        assert bounded_manifest["sessionPlanAgeGate"] == bounded_manifest["reviewGates"]["planFresh"]
        assert not bounded_manifest["reviewGates"]["planFresh"]["passed"]
        bounded_summary = helper.summarize_signal_proof_manifest(
            Path(tmp) / "bounded-session-out" / "manifest.json",
            bounded_manifest,
        )
        assert "planFresh" in bounded_summary["failedReviewGateNames"]


def test_fishability_fan_suggested_commands(helper) -> None:
    candidates, _geometry = helper.generate_fan_candidates(
        origin_x=100,
        origin_y=100,
        forward_x=100,
        forward_y=0,
        distances=[50],
        laterals=[0],
        max_points=1,
        client_width=300,
        client_height=300,
    )
    assert candidates[0]["inBounds"]

    commands = helper.build_reticle_candidate_commands(
        pid=1234,
        hwnd=0x1234,
        x=candidates[0]["clientX"],
        y=candidates[0]["clientY"],
        key="8",
        watch_seconds=2.0,
    )
    assert "--dry-run" in commands["reticleDryRun"]
    assert "--confirm-input --skip-click --cancel-after-key" in commands["reticleSkipClickCancel"]
    assert "--x 100" in commands["reticleDryRun"]
    assert "--y 50" in commands["reticleDryRun"]


def test_fishability_fan_runbook_render(helper) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-fan-runbook-") as tmp:
        manifest_path = Path(tmp) / "manifest.json"
        manifest = {
            "schema": "autofish.signalProof.fishabilityFan.v1",
            "generatedAtUtc": "2026-05-26T00:00:00+00:00",
            "request": {
                "pid": 1234,
                "originX": 100,
                "originY": 100,
                "forwardX": 100,
                "forwardY": 0,
            },
            "target": {"hwnd": "0x1234"},
            "candidates": [
                {
                    "index": 0,
                    "name": "d50_l0",
                    "clientX": 100,
                    "clientY": 50,
                    "inBounds": True,
                    "suggestedCommands": helper.build_reticle_candidate_commands(
                        pid=1234,
                        hwnd=0x1234,
                        x=100,
                        y=50,
                        key="8",
                        watch_seconds=2.0,
                    ),
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        markdown = helper.render_fishability_fan_runbook(str(manifest_path))
        assert "Candidate 0" in markdown
        assert "reticle --pid 1234" in markdown
        assert "--skip-click --cancel-after-key" in markdown
        assert "session-plan from-fan" in markdown
        assert "session-plan runbook" in markdown
        assert "they send no left click and no movement" in markdown


def test_session_plan_from_fan_candidate(helper) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-plan-from-fan-") as tmp:
        manifest_path = Path(tmp) / "manifest.json"
        manifest = {
            "schema": "autofish.signalProof.fishabilityFan.v1",
            "generatedAtUtc": "2026-05-26T00:00:00+00:00",
            "request": {"pid": 1234, "hwnd": "0x1234", "key": "8"},
            "target": {
                "hwnd": "0x1234",
                "ownerProcessId": 1234,
                "clientWidth": 1280,
                "clientHeight": 720,
                "clientScreenX": 40,
                "clientScreenY": 80,
            },
            "effectiveClient": {"width": 1280, "height": 720, "source": "live-target"},
            "candidates": [
                {
                    "index": 0,
                    "name": "d50_l0",
                    "clientX": 100,
                    "clientY": 50,
                    "inBounds": True,
                    "plannedClassification": "unproven-pending-game-feedback",
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        args = argparse.Namespace(
            manifest=str(manifest_path),
            candidate_index=0,
            candidate_name=None,
            profile="starter-pond",
            profile_root="profiles",
            key=None,
            max_casts=3,
            max_allowed_casts=10,
            pull_clicks=1,
            cast_wait_seconds=None,
            post_pull_delay_ms=None,
            inter_cast_delay_ms=800,
            stop_file=str(Path(tmp) / "STOP.txt"),
            validate_target=False,
        )
        plan = helper.build_session_plan_from_fan(args)
        assert plan["target"]["pid"] == 1234
        assert plan["target"]["hwnd"] == "0x1234"
        assert plan["fishablePoint"]["x"] == 100
        assert plan["fishablePoint"]["y"] == 50
        assert plan["profile"]["id"] == "starter-pond"
        assert plan["source"]["type"] == "fishabilityFanCandidate"
        assert plan["safety"]["requiresReviewedFishableCandidateBeforeConfirmInput"]
        assert plan["targetValidation"]["clientWidth"] == 1280
        assert plan["targetValidation"]["clientHeight"] == 720
        assert plan["targetValidation"]["clientScreenX"] == 40
        assert plan["targetValidation"]["clientScreenY"] == 80
        assert plan["targetValidation"]["clientSizeSource"] == "live-target"
        stale_target_gate = helper.check_session_plan_target_freshness(
            {"plan": plan},
            {"clientWidth": 640, "clientHeight": 360, "isMinimized": False},
        )
        assert stale_target_gate["required"]
        assert not stale_target_gate["passed"]
        assert "stale" in stale_target_gate["reason"]
        scope_token = plan["review"]["scopeToken"]
        assert scope_token.startswith("afscope-")
        gate = helper.check_fan_candidate_review_gate(
            {"plan": plan},
            str(Path(tmp) / "missing-decisions.json"),
            allow_unreviewed=False,
        )
        assert gate["required"]
        assert not gate["passed"]

        bypassed_gate = helper.check_fan_candidate_review_gate(
            {"plan": plan},
            str(Path(tmp) / "missing-decisions.json"),
            allow_unreviewed=True,
        )
        assert bypassed_gate["passed"]
        assert bypassed_gate["overridden"]

        decision_register = Path(tmp) / "decisions.json"
        decision_register.write_text(
            json.dumps(
                {
                    "schema": "autofish.signalProof.decisions.v1",
                    "entries": [
                        {
                            "signal": "fishabilityCandidate",
                            "decision": "fallback-only",
                            "scopeTokens": [scope_token],
                        }
                    ],
                    "latestBySignal": {
                        "fishabilityCandidate": {
                            "signal": "fishabilityCandidate",
                            "decision": "fallback-only",
                            "scopeTokens": ["different-token"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        scoped_gate = helper.check_fan_candidate_review_gate(
            {"plan": plan},
            str(decision_register),
            allow_unreviewed=False,
        )
        assert scoped_gate["passed"]
        assert scoped_gate["requiresScopeMatch"]
        assert scoped_gate["latestFishabilityCandidateDecision"]["scopeTokens"] == [scope_token]

        plan_path = Path(tmp) / "session-plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        markdown = helper.render_session_plan_runbook(str(plan_path), ".autofish-live")
        assert "--signal fishabilityCandidate" in markdown
        assert f"--session-plan '{plan_path}'" in markdown
        assert "session-plan gates" in markdown
        assert "session-plan explain" in markdown
        assert "session-plan preflight" in markdown
        checklist = helper.render_session_plan_checklist(str(plan_path), ".autofish-live", str(decision_register))
        assert "Fishability candidate has a scoped reviewed decision" in checklist
        assert "--signal fishabilityCandidate" in checklist
        with contextlib.redirect_stdout(io.StringIO()) as checklist_output:
            assert (
                helper.run_session_plan_checklist(
                    argparse.Namespace(
                        path=str(plan_path),
                        proof_root=".autofish-live",
                        decision_register=str(decision_register),
                        max_plan_age_minutes=0,
                        output=None,
                    )
                )
                == 0
            )
        assert "AutoFish Session Plan Checklist" in checklist_output.getvalue()
        assert "--require ready-one-cast" in markdown
        assert "--require ready-bounded-session" in markdown
        assert "session-plan stop-file create" in markdown
        assert "session-plan stop-file clear" in markdown
        assert "Fan-derived plans also require" in markdown

        with contextlib.redirect_stdout(io.StringIO()) as gate_output:
            assert (
                helper.run_session_plan_gates(
                    argparse.Namespace(path=str(plan_path), decision_register=str(decision_register), require=None)
                )
                == 0
            )
        gate_report = json.loads(gate_output.getvalue())
        assert gate_report["schema"] == "autofish.sessionPlan.reviewGates.v1"
        assert gate_report["readiness"]["stopFileClear"]
        assert gate_report["readiness"]["planFresh"]
        assert "targetForeground" in gate_report["readiness"]
        assert "clientReadable" in gate_report["readiness"]
        assert gate_report["readiness"]["confirmedOneCast"]
        assert not gate_report["readiness"]["confirmedBoundedSession"]
        assert not gate_report["readiness"]["readyForOneCast"]
        explanation = helper.render_session_plan_gate_explanation(gate_report)
        assert "AutoFish Session Plan Gate Explanation" in explanation
        assert "sends game input: `no`" in explanation
        assert "required readiness: `-`" in explanation
        assert "## Next action" in explanation
        with contextlib.redirect_stdout(io.StringIO()) as explain_output:
            assert (
                helper.run_session_plan_explain(
                    argparse.Namespace(
                        path=str(plan_path),
                        decision_register=str(decision_register),
                        max_plan_age_minutes=0,
                        output=None,
                    )
                )
                == 0
            )
        assert "AutoFish Session Plan Gate Explanation" in explain_output.getvalue()
        with contextlib.redirect_stdout(io.StringIO()) as preflight_pass_output:
            assert (
                helper.run_session_plan_preflight(
                    argparse.Namespace(
                        path=str(plan_path),
                        decision_register=str(decision_register),
                        max_plan_age_minutes=0,
                        require=["confirmed-one-cast"],
                        output=None,
                    )
                )
                == 0
            )
        assert "failing required readiness: `-`" in preflight_pass_output.getvalue()
        with contextlib.redirect_stdout(io.StringIO()) as preflight_fail_output:
            assert (
                helper.run_session_plan_preflight(
                    argparse.Namespace(
                        path=str(plan_path),
                        decision_register=str(decision_register),
                        max_plan_age_minutes=0,
                        require=["ready-one-cast"],
                        output=None,
                    )
                )
                == 1
            )
        assert "failing required readiness: `ready-one-cast`" in preflight_fail_output.getvalue()
        with contextlib.redirect_stdout(io.StringIO()):
            assert (
                helper.run_session_plan_gates(
                    argparse.Namespace(
                        path=str(plan_path),
                        decision_register=str(decision_register),
                        require=["confirmed-one-cast"],
                    )
                )
                == 0
            )
        with contextlib.redirect_stdout(io.StringIO()):
            assert (
                helper.run_session_plan_gates(
                    argparse.Namespace(
                        path=str(plan_path),
                        decision_register=str(decision_register),
                        require=["confirmed-bounded-session"],
                    )
                )
                == 1
            )

        stop_file = Path(tmp) / "STOP.txt"
        stop_file.write_text("stop", encoding="utf-8")
        stop_gate = helper.check_session_plan_stop_file_gate({"plan": plan})
        assert stop_gate["required"]
        assert not stop_gate["passed"]
        assert stop_gate["exists"]
        with contextlib.redirect_stdout(io.StringIO()):
            assert (
                helper.run_session_plan_gates(
                    argparse.Namespace(
                        path=str(plan_path),
                        decision_register=str(decision_register),
                        require=["stop-file-clear"],
                    )
                )
                == 1
            )
        stop_file.unlink()

        with contextlib.redirect_stdout(io.StringIO()) as status_output:
            assert (
                helper.run_session_plan_stop_file(
                    argparse.Namespace(path=str(plan_path), stop_file_action="status")
                )
                == 0
            )
        status_report = json.loads(status_output.getvalue())
        assert status_report["schema"] == "autofish.sessionPlan.stopFile.v1"
        assert not status_report["existsAfter"]
        assert not status_report["mutated"]

        with contextlib.redirect_stdout(io.StringIO()) as create_output:
            assert (
                helper.run_session_plan_stop_file(
                    argparse.Namespace(path=str(plan_path), stop_file_action="create")
                )
                == 0
            )
        create_report = json.loads(create_output.getvalue())
        assert create_report["existsAfter"]
        assert create_report["mutated"]
        assert stop_file.exists()

        with contextlib.redirect_stdout(io.StringIO()) as clear_output:
            assert (
                helper.run_session_plan_stop_file(
                    argparse.Namespace(path=str(plan_path), stop_file_action="clear")
                )
                == 0
            )
        clear_report = json.loads(clear_output.getvalue())
        assert not clear_report["existsAfter"]
        assert clear_report["mutated"]
        assert not stop_file.exists()

        valid_evidence = Path(tmp) / "one-cast-proof" / "manifest.json"
        valid_evidence.parent.mkdir(parents=True, exist_ok=True)
        valid_evidence.write_text(
            json.dumps(
                {
                    "schema": "autofish.signalProof.oneCast.v1",
                    "generatedAtUtc": "2026-05-26T00:00:00+00:00",
                    "mode": "confirm-input",
                    "request": {},
                    "safety": {},
                    "captures": [],
                    "actions": [],
                    "result": {"completed": True, "liveInputSent": True},
                    "decision": {"classification": "evidence-only"},
                    "reviewGates": {},
                }
            ),
            encoding="utf-8",
        )
        register_output = Path(tmp) / "recorded-decisions.json"
        with contextlib.redirect_stdout(io.StringIO()) as decide_output:
            assert (
                helper.run_signal_proof_decide(
                    argparse.Namespace(
                        signal="fishabilityCandidate",
                        decision="fallback-only",
                        reason="Reviewed candidate in smoke test.",
                        evidence=[str(valid_evidence), "evidence/manifest.json"],
                        proof_root=".autofish-live",
                        operator=None,
                        note=None,
                        register=str(register_output),
                        scope_token=None,
                        session_plan=[str(plan_path)],
                    )
                )
                == 0
            )
        decide_result = json.loads(decide_output.getvalue())
        assert decide_result["entry"]["scopeTokens"] == [scope_token]
        assert decide_result["entry"]["sessionPlanScopes"][0]["path"] == str(plan_path)
        evidence_validation = decide_result["entry"]["evidenceValidation"]
        assert evidence_validation[0]["status"] == "signal-proof-manifest"
        assert evidence_validation[0]["manifestShapeValid"]
        assert evidence_validation[0]["signal"] == "oneCast"
        assert evidence_validation[1]["status"] == "missing"


def test_session_plan_target_freshness_gate(helper) -> None:
    plan = {
        "schema": "autofish.sessionPlan.v1",
        "target": {"pid": 1234, "hwnd": "0x1234"},
        "targetValidation": {"clientWidth": 1280, "clientHeight": 720, "clientSizeSource": "live-target"},
    }
    matching_gate = helper.check_session_plan_target_freshness(
        {"plan": plan},
        {"clientWidth": 1280, "clientHeight": 720, "isMinimized": False},
    )
    assert matching_gate["required"]
    assert matching_gate["passed"]

    stale_gate = helper.check_session_plan_target_freshness(
        {"plan": plan},
        {"clientWidth": 1024, "clientHeight": 768, "isMinimized": False},
    )
    assert stale_gate["required"]
    assert not stale_gate["passed"]
    assert stale_gate["expectedClientWidth"] == 1280
    assert stale_gate["currentClientHeight"] == 768

    unrecorded_gate = helper.check_session_plan_target_freshness({"plan": {"schema": "autofish.sessionPlan.v1"}})
    assert not unrecorded_gate["required"]
    assert unrecorded_gate["passed"]

    now = helper.datetime(2026, 5, 26, 12, 0, tzinfo=helper.timezone.utc)
    fresh_age_gate = helper.check_session_plan_age_gate(
        {"plan": {**plan, "generatedAtUtc": "2026-05-26T11:30:00+00:00"}},
        max_age_minutes=60,
        now=now,
    )
    assert fresh_age_gate["required"]
    assert fresh_age_gate["passed"]
    assert fresh_age_gate["ageMinutes"] == 30

    stale_age_gate = helper.check_session_plan_age_gate(
        {"plan": {**plan, "generatedAtUtc": "2026-05-26T11:30:00+00:00"}},
        max_age_minutes=10,
        now=now,
    )
    assert stale_age_gate["required"]
    assert not stale_age_gate["passed"]

    disabled_age_gate = helper.check_session_plan_age_gate(
        {"plan": {**plan, "generatedAtUtc": "2026-05-26T11:30:00+00:00"}},
        max_age_minutes=0,
        now=now,
    )
    assert not disabled_age_gate["required"]
    assert disabled_age_gate["passed"]

    future_age_gate = helper.check_session_plan_age_gate(
        {"plan": {**plan, "generatedAtUtc": "2026-05-26T12:05:00+00:00"}},
        max_age_minutes=60,
        now=now,
    )
    assert not future_age_gate["passed"]
    assert "future" in future_age_gate["reason"]

    direct_cli_age_gate = helper.check_session_plan_age_gate(None, now=now)
    assert not direct_cli_age_gate["required"]
    assert direct_cli_age_gate["passed"]

    ready_target = {
        "hwnd": "0x1234",
        "foregroundWindow": "0x1234",
        "foregroundMatches": True,
        "clientWidth": 1280,
        "clientHeight": 720,
        "isMinimized": False,
    }
    foreground_gate = helper.check_session_plan_foreground_gate({"plan": plan}, ready_target)
    assert foreground_gate["required"]
    assert foreground_gate["passed"]
    readability_gate = helper.check_session_plan_readability_gate({"plan": plan}, ready_target)
    assert readability_gate["required"]
    assert readability_gate["passed"]

    background_gate = helper.check_session_plan_foreground_gate(
        {"plan": plan},
        {**ready_target, "foregroundWindow": "0x9999", "foregroundMatches": False},
    )
    assert not background_gate["passed"]

    tiny_gate = helper.check_session_plan_readability_gate(
        {"plan": plan},
        {**ready_target, "clientWidth": 640, "clientHeight": 360},
    )
    assert not tiny_gate["passed"]
    assert tiny_gate["preferredMinimumClientWidth"] == helper.PREFERRED_READABLE_CLIENT_WIDTH


def test_scoped_one_cast_gate(helper) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-onecast-gate-") as tmp:
        args = argparse.Namespace(
            pid=1234,
            hwnd="0x1234",
            x=100,
            y=50,
            profile="starter-pond",
            profile_root="profiles",
            key="8",
            max_casts=3,
            max_allowed_casts=10,
            pull_clicks=1,
            cast_wait_seconds=None,
            post_pull_delay_ms=None,
            inter_cast_delay_ms=800,
            stop_file=None,
            validate_target=False,
        )
        plan = helper.build_session_plan(args)
        scope_token = plan["review"]["scopeToken"]
        register_path = Path(tmp) / "decisions.json"
        register_path.write_text(
            json.dumps(
                {
                    "schema": "autofish.signalProof.decisions.v1",
                    "entries": [
                        {"signal": "oneCast", "decision": "fallback-only", "scopeTokens": [scope_token]}
                    ],
                    "latestBySignal": {
                        "oneCast": {
                            "signal": "oneCast",
                            "decision": "fallback-only",
                            "scopeTokens": ["stale-token"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        gate_args = argparse.Namespace(
            allow_unreviewed_one_cast=False,
            decision_register=str(register_path),
        )
        gate = helper.check_one_cast_review_gate(gate_args, {"plan": plan})
        assert gate["passed"]
        assert gate["requiresScopeMatch"]
        assert gate["latestOneCastDecision"]["scopeTokens"] == [scope_token]


def main() -> int:
    helper = load_helper()
    doc_validator = load_doc_validator()
    test_doc_command_validator_surface(helper, doc_validator)
    test_profile_defaults(helper)
    test_session_plan_defaults(helper)
    test_runbook_render(helper, doc_validator)
    test_session_plan_doctor_report(helper, doc_validator)
    test_autofish_doctor_bundle(helper, doc_validator)
    test_direct_live_command_stop_file_defaults(helper)
    test_red_reticle_click_guard(helper)
    test_red_reticle_guard_summary(helper)
    test_manifest_shape_validation_summary(helper)
    test_signal_proof_doctor_report(helper)
    test_facing_delta_manifest_result_is_always_dict(helper)
    test_facing_from_coords_manual_delta(helper)
    test_target_snapshot_invalid_hwnd(helper)
    test_stale_session_plan_refuses_plan_backed_proofs(helper)
    test_fishability_fan_suggested_commands(helper)
    test_fishability_fan_runbook_render(helper)
    test_session_plan_from_fan_candidate(helper)
    test_session_plan_target_freshness_gate(helper)
    test_scoped_one_cast_gate(helper)
    print("AutoFish Python helper smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
