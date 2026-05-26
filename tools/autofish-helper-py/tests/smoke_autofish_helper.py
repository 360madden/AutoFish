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
        assert "they send no left click and no movement" in markdown


def test_session_plan_from_fan_candidate(helper) -> None:
    with tempfile.TemporaryDirectory(prefix="autofish-helper-plan-from-fan-") as tmp:
        manifest_path = Path(tmp) / "manifest.json"
        manifest = {
            "schema": "autofish.signalProof.fishabilityFan.v1",
            "generatedAtUtc": "2026-05-26T00:00:00+00:00",
            "request": {"pid": 1234, "hwnd": "0x1234", "key": "8"},
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


def main() -> int:
    helper = load_helper()
    test_profile_defaults(helper)
    test_session_plan_defaults(helper)
    test_runbook_render(helper)
    test_direct_live_command_stop_file_defaults(helper)
    test_fishability_fan_suggested_commands(helper)
    test_fishability_fan_runbook_render(helper)
    test_session_plan_from_fan_candidate(helper)
    print("AutoFish Python helper smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
