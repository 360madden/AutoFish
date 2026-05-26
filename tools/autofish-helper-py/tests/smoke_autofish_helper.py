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
        assert "No command in this runbook sends movement" in markdown


def main() -> int:
    helper = load_helper()
    test_profile_defaults(helper)
    test_session_plan_defaults(helper)
    test_runbook_render(helper)
    print("AutoFish Python helper smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
