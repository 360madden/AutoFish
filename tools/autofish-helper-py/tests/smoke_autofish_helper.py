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


def load_helper():
    spec = importlib.util.spec_from_file_location("autofish_helper", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helper module from {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_runbook_render(helper) -> None:
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
        assert "signal-proof one-cast --session-plan" in markdown
        assert "signal-proof bounded-session --session-plan" in markdown
        assert "--signal oneCast" in markdown
        assert "New-Item -ItemType File -Force -Path" in markdown
        assert ".autofish-live/STOP.txt" in markdown
        assert "No command in this runbook sends movement" in markdown


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
            stop_file=None,
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
        assert gate_report["readiness"]["confirmedOneCast"]
        assert not gate_report["readiness"]["confirmedBoundedSession"]
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

        register_output = Path(tmp) / "recorded-decisions.json"
        with contextlib.redirect_stdout(io.StringIO()) as decide_output:
            assert (
                helper.run_signal_proof_decide(
                    argparse.Namespace(
                        signal="fishabilityCandidate",
                        decision="fallback-only",
                        reason="Reviewed candidate in smoke test.",
                        evidence=["evidence/manifest.json"],
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
    test_profile_defaults(helper)
    test_session_plan_defaults(helper)
    test_runbook_render(helper)
    test_direct_live_command_stop_file_defaults(helper)
    test_fishability_fan_suggested_commands(helper)
    test_fishability_fan_runbook_render(helper)
    test_session_plan_from_fan_candidate(helper)
    test_session_plan_target_freshness_gate(helper)
    test_scoped_one_cast_gate(helper)
    print("AutoFish Python helper smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
