"""
generate_haptic_graph.py

Senior-level, modular script for HIL-style haptic collision analysis.

Pipeline summary:
1) Collect (simulated) telemetry at 60 Hz for exactly 10 seconds.
2) Actuate a downward sweeping arc motion (pyautogui when available, mock otherwise).
3) Parse telemetry and compute instantaneous hammer velocity (pixels/frame).
4) Detect a contact-rich haptic transition event.
5) Produce and save a high-resolution dual-axis scientific plot.

Telemetry format expected:
STATE|P:x,y|H:x,y|A:y|D:deg
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ----------------------------- Configuration ----------------------------- #
FPS: int = 60
DURATION_SECONDS: float = 10.0
TOTAL_FRAMES: int = int(FPS * DURATION_SECONDS)
OUTPUT_PLOT_PATH: str = "Haptic_Collision_Data_Analysis.png"


# ----------------------------- Telemetry Model ---------------------------- #
@dataclass
class TelemetrySample:
    """Strongly-typed telemetry container extracted from one STATE string."""

    pot_x: float
    pot_y: float
    hammer_x: float
    hammer_y: float
    altitude: float
    angle_deg: float


# Strict parser for the exact telemetry layout.
STATE_PATTERN = re.compile(
    r"^STATE\|P:(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\|"
    r"H:(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\|"
    r"A:(-?\d+(?:\.\d+)?)\|D:(-?\d+(?:\.\d+)?)$"
)


def parse_state_string(state_line: str) -> TelemetrySample:
    """
    Parse one STATE line.

    Replace this parser only if your upstream string format changes.
    """
    match = STATE_PATTERN.match(state_line.strip())
    if not match:
        raise ValueError(f"Telemetry string does not match expected format: {state_line}")

    p_x, p_y, h_x, h_y, altitude, angle = map(float, match.groups())
    return TelemetrySample(
        pot_x=p_x,
        pot_y=p_y,
        hammer_x=h_x,
        hammer_y=h_y,
        altitude=altitude,
        angle_deg=angle,
    )


# --------------------------- Receiver / Actuator -------------------------- #
class DummyTelemetryReceiver:
    """
    Deterministic 60 Hz telemetry simulator.

    IMPORTANT:
    - Replace `get_state()` with your Selenium/WebSocket receiver callback.
    - Keep return format exactly: STATE|P:x,y|H:x,y|A:y|D:deg
    """

    def __init__(self, total_frames: int, fps: int):
        self.total_frames = total_frames
        self.fps = fps
        self.frame_idx = 0

    def get_state(self) -> str:
        """
        Generate synthetic hammer swing + collision dynamics:
        - First ~65%: descending/sweeping motion with moderate velocity.
        - Collision zone: sudden velocity collapse.
        - Post-contact: altitude rebounds/increases.
        """
        t = self.frame_idx / self.fps
        progress = min(self.frame_idx / max(1, self.total_frames - 1), 1.0)

        # Pot is mostly stationary in this toy simulator.
        pot_x = 550.0
        pot_y = 540.0

        # Parametric arc for hammer movement.
        arc_theta = np.pi * (0.25 + 1.15 * progress)  # sweeping range
        radius = 185.0 - 30.0 * progress
        base_x = 610.0 + radius * math.cos(arc_theta)
        base_y = 290.0 + radius * math.sin(arc_theta)

        # Contact window around 6.4 s causes abrupt velocity drop.
        t_contact = 6.4
        if t < t_contact:
            hammer_x = base_x
            hammer_y = base_y + 65.0 * progress
            altitude = max(15.0, 250.0 - 34.0 * t)  # descending
        else:
            # Near-stationary hammer after impact.
            hammer_x = 545.0 + 1.2 * math.sin(22.0 * t)
            hammer_y = 542.0 + 1.0 * math.cos(24.0 * t)
            altitude = 35.0 + 20.0 * (t - t_contact)  # rebound/increase

        # Angle is synthetic but consistent with swing progression.
        angle_deg = -110.0 + 200.0 * progress

        self.frame_idx += 1
        return (
            f"STATE|P:{pot_x:.2f},{pot_y:.2f}|"
            f"H:{hammer_x:.2f},{hammer_y:.2f}|"
            f"A:{altitude:.2f}|D:{angle_deg:.2f}"
        )


class MouseActuator:
    """
    Actuator wrapper:
    - Uses pyautogui when available.
    - Falls back to a mock/no-op mode for headless or CI execution.
    """

    def __init__(self) -> None:
        self.enabled = False
        self.pyautogui = None
        try:
            import pyautogui  # type: ignore

            self.pyautogui = pyautogui
            # Disable fail-safe delay for smooth 60 Hz behavior.
            self.pyautogui.PAUSE = 0
            self.enabled = True
        except Exception:
            self.enabled = False

    def move_in_downward_arc(self, frame_idx: int, total_frames: int) -> None:
        """
        Compute one point on a downward sweeping arc and move cursor there.

        In mock mode, this function intentionally does nothing.
        """
        progress = min(frame_idx / max(1, total_frames - 1), 1.0)
        theta = np.pi * (0.20 + 1.10 * progress)
        cx, cy = 960, 360
        rx, ry = 320, 260
        target_x = int(cx + rx * math.cos(theta))
        target_y = int(cy + ry * math.sin(theta) + 130.0 * progress)

        if self.enabled and self.pyautogui is not None:
            self.pyautogui.moveTo(target_x, target_y, duration=0)


# ----------------------------- Core Analytics ----------------------------- #
def compute_velocity(
    prev_hammer_xy: Optional[Tuple[float, float]], current_hammer_xy: Tuple[float, float]
) -> float:
    """Velocity in pixels/frame using Euclidean displacement."""
    if prev_hammer_xy is None:
        return 0.0
    dx = current_hammer_xy[0] - prev_hammer_xy[0]
    dy = current_hammer_xy[1] - prev_hammer_xy[1]
    return float(math.hypot(dx, dy))


def detect_haptic_event(df: pd.DataFrame) -> Optional[int]:
    """
    Identify 'contact-rich transition':
    - Velocity drops sharply to near zero.
    - Altitude trend turns positive (begins increasing).
    Returns DataFrame index of event frame if detected.
    """
    if len(df) < 5:
        return None

    vel = df["hammer_velocity"].to_numpy()
    alt = df["altitude"].to_numpy()

    # 3-frame moving averages dampen sensor jitter while keeping latency low.
    vel_smooth = pd.Series(vel).rolling(window=3, min_periods=1).mean().to_numpy()
    alt_diff = np.diff(alt, prepend=alt[0])
    alt_diff_smooth = pd.Series(alt_diff).rolling(window=3, min_periods=1).mean().to_numpy()

    # Adaptive threshold from first half of trial (pre-contact behavior).
    baseline_slice = vel_smooth[: max(10, len(vel_smooth) // 2)]
    baseline_median = float(np.median(baseline_slice))
    near_zero_threshold = max(0.9, 0.18 * baseline_median)

    # Large negative velocity derivative indicates an abrupt deceleration.
    vel_drop = np.diff(vel_smooth, prepend=vel_smooth[0])

    for i in range(3, len(df)):
        sharp_drop = vel_drop[i] < -0.9
        near_zero = vel_smooth[i] <= near_zero_threshold
        altitude_rebound = alt_diff_smooth[i] > 0.25
        if sharp_drop and near_zero and altitude_rebound:
            return i

    return None


def build_scientific_plot(df: pd.DataFrame, event_idx: Optional[int], output_path: str) -> None:
    """Generate and save a publication-style dual-axis line graph."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax_left = plt.subplots(figsize=(13, 7.5), dpi=180)

    # Left axis: hammer velocity
    velocity_line = ax_left.plot(
        df["timestamp_sec"],
        df["hammer_velocity"],
        color="#0B5ED7",
        linewidth=2.1,
        label="Hammer Velocity (Pixels/frame)",
    )[0]
    ax_left.set_xlabel("Time (seconds)", fontsize=13)
    ax_left.set_ylabel("Hammer Velocity (Pixels/frame)", color="#0B5ED7", fontsize=12)
    ax_left.tick_params(axis="y", labelcolor="#0B5ED7")

    # Right axis: altitude
    ax_right = ax_left.twinx()
    altitude_line = ax_right.plot(
        df["timestamp_sec"],
        df["altitude"],
        color="#C1121F",
        linewidth=2.1,
        label="Altitude (Pixels)",
    )[0]
    ax_right.set_ylabel("Altitude (Pixels)", color="#C1121F", fontsize=12)
    ax_right.tick_params(axis="y", labelcolor="#C1121F")

    # Event marker and annotation
    if event_idx is not None:
        event_t = float(df.loc[event_idx, "timestamp_sec"])
        event_v = float(df.loc[event_idx, "hammer_velocity"])
        ax_left.axvline(event_t, color="black", linestyle="--", linewidth=1.5, alpha=0.9)
        ax_left.annotate(
            "Contact-Rich Transition\n(Proprioceptive Collision)",
            xy=(event_t, event_v),
            xytext=(event_t + 0.45, max(df["hammer_velocity"]) * 0.78),
            arrowprops=dict(arrowstyle="->", lw=1.1, color="black"),
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.95),
        )

    # Academic-style chart details.
    ax_left.set_title(
        "Haptic Collision Data Analysis: Hammer Velocity vs Altitude",
        fontsize=14,
        weight="bold",
        pad=12,
    )
    ax_left.grid(which="major", linestyle="--", linewidth=0.65, alpha=0.6)
    fig.tight_layout()

    # Unified legend from both axes.
    lines = [velocity_line, altitude_line]
    labels = [ln.get_label() for ln in lines]
    ax_left.legend(lines, labels, loc="upper right", frameon=True)

    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def run_collection_loop(
    receiver_fn: Callable[[], str],
    actuator: MouseActuator,
    duration_seconds: float = DURATION_SECONDS,
    fps: int = FPS,
) -> pd.DataFrame:
    """
    Main 10-second collection loop.

    Exactly `duration_seconds * fps` frames are sampled.
    """
    total_frames = int(duration_seconds * fps)
    frame_period = 1.0 / fps

    records = []
    prev_hammer_xy: Optional[Tuple[float, float]] = None

    t0 = time.perf_counter()
    for frame_idx in range(total_frames):
        scheduled_time = t0 + frame_idx * frame_period

        # Actuate swing trajectory (real or mocked).
        actuator.move_in_downward_arc(frame_idx=frame_idx, total_frames=total_frames)

        # Acquire one telemetry state line.
        state_line = receiver_fn()
        parsed = parse_state_string(state_line)

        curr_hammer_xy = (parsed.hammer_x, parsed.hammer_y)
        velocity = compute_velocity(prev_hammer_xy, curr_hammer_xy)
        prev_hammer_xy = curr_hammer_xy

        timestamp_sec = frame_idx * frame_period
        records.append(
            {
                "timestamp_sec": timestamp_sec,
                "hammer_velocity": velocity,
                "altitude": parsed.altitude,
            }
        )

        # Timing control for stable 60 Hz acquisition.
        remaining = scheduled_time + frame_period - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)

    return pd.DataFrame.from_records(records)


def main() -> None:
    """
    Entry point.

    To integrate your live pipeline:
    1) Replace DummyTelemetryReceiver with your receiver object.
    2) Pass your receiver callback into run_collection_loop(...).
    """
    telemetry_receiver = DummyTelemetryReceiver(total_frames=TOTAL_FRAMES, fps=FPS)
    actuator = MouseActuator()

    df = run_collection_loop(
        receiver_fn=telemetry_receiver.get_state,
        actuator=actuator,
        duration_seconds=DURATION_SECONDS,
        fps=FPS,
    )

    event_idx = detect_haptic_event(df)
    build_scientific_plot(df=df, event_idx=event_idx, output_path=OUTPUT_PLOT_PATH)

    print(f"Saved plot: {OUTPUT_PLOT_PATH}")
    if event_idx is not None:
        event_time = df.loc[event_idx, "timestamp_sec"]
        print(f"Detected haptic event at t={event_time:.3f}s (frame {event_idx}).")
    else:
        print("Haptic event not detected under current thresholds.")


if __name__ == "__main__":
    main()
