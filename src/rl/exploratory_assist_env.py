"""Software-only RL environment with separate ideal human and exoskeleton torques."""

from __future__ import annotations

import json
import math
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_mot(path: Path) -> tuple[list[str], np.ndarray]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    end = next(index for index, line in enumerate(lines) if line.strip().lower() == "endheader")
    in_degrees = any(line.strip().lower() == "indegrees=yes" for line in lines[: end + 1])
    columns = lines[end + 1].split()
    values = np.asarray([
        [float(value) for value in line.split()]
        for line in lines[end + 2:] if line.strip()
    ])
    if values.ndim != 2 or values.shape[1] != len(columns):
        raise ValueError(f"invalid MOT file: {path}")
    if in_degrees:
        values[:, 1:] = np.radians(values[:, 1:])
    return columns, values


class ExploratoryAssistEnv(gym.Env):
    """Track a synthetic 2-DOF trajectory while RL controls only exo motors."""

    metadata = {"render_modes": []}

    def __init__(self, config_path: str | Path = "config/rl/exploratory_sandbox_v1.json"):
        super().__init__()
        self.config_path = resolve(config_path)
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        if self.config.get("status") != "SOFTWARE_EXPLORATION_ONLY":
            raise ValueError("sandbox config must remain SOFTWARE_EXPLORATION_ONLY")
        self.model = mujoco.MjModel.from_xml_path(str(resolve(self.config["model"])))
        self.data = mujoco.MjData(self.model)
        self.joint_names = [
            mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, index)
            for index in range(self.model.njnt)
        ]
        actuator_names = [
            mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, index)
            for index in range(self.model.nu)
        ]
        human_names = self.config["human_controller"]["actuators"]
        self.human_indices = np.asarray([actuator_names.index(name) for name in human_names], dtype=int)
        prefix = self.config["exoskeleton"]["actuator_prefix"]
        self.exo_indices = np.asarray([
            index for index, name in enumerate(actuator_names) if name and name.startswith(prefix)
        ], dtype=int)
        if len(self.human_indices) != self.model.nv or len(self.exo_indices) != self.model.nv:
            raise ValueError("sandbox requires one human and one exo motor per scalar DOF")
        for index in np.concatenate([self.human_indices, self.exo_indices]):
            if not self.model.actuator_ctrllimited[index]:
                raise ValueError(f"actuator without ctrlrange: {actuator_names[index]}")

        columns, target = read_mot(resolve(self.config["target"]))
        self.target_time = target[:, 0]
        self.target_qpos = np.column_stack([
            target[:, columns.index(name)] for name in self.joint_names
        ])
        self.kp = np.asarray(self.config["human_controller"]["kp_nm_per_rad"], dtype=float)
        self.kd = np.asarray(self.config["human_controller"]["kd_nms_per_rad"], dtype=float)
        self.human_limits = np.asarray(self.config["human_controller"]["torque_limits_nm"], dtype=float)
        model_human_ranges = self.model.actuator_ctrlrange[self.human_indices]
        if not np.allclose(model_human_ranges[:, 0], -self.human_limits) or not np.allclose(
            model_human_ranges[:, 1], self.human_limits
        ):
            raise ValueError("configured human torque limits do not match the MuJoCo model")
        self.exo_ranges = self.model.actuator_ctrlrange[self.exo_indices].copy()
        configured_exo_limits = np.asarray(self.config["exoskeleton"]["torque_limits_nm"], dtype=float)
        if not np.allclose(self.exo_ranges[:, 0], -configured_exo_limits) or not np.allclose(
            self.exo_ranges[:, 1], configured_exo_limits
        ):
            raise ValueError("configured exo torque limits do not match the MuJoCo model")
        reward = self.config["reward"]
        self.weights = np.asarray([
            reward["tracking_weight"], reward["human_effort_weight"],
            reward["exo_effort_weight"], reward["smoothness_weight"], reward["safety_weight"],
        ], dtype=float)
        self.previous_action = np.zeros(len(self.exo_indices), dtype=np.float32)
        observation_size = 5 * self.model.nv + len(self.exo_indices) + 2
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(observation_size,), dtype=np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(len(self.exo_indices),), dtype=np.float32)

    def target_at(self, time_s: float) -> tuple[np.ndarray, np.ndarray]:
        position = np.asarray([
            np.interp(time_s, self.target_time, self.target_qpos[:, index])
            for index in range(self.model.nv)
        ])
        dt = max(float(self.model.opt.timestep), 1e-4)
        before = np.asarray([
            np.interp(max(0.0, time_s - dt), self.target_time, self.target_qpos[:, index])
            for index in range(self.model.nv)
        ])
        velocity = (position - before) / dt
        return position, velocity

    def _phase(self) -> tuple[float, float]:
        progress = np.clip(self.data.time / self.target_time[-1], 0.0, 1.0)
        angle = 2.0 * math.pi * progress
        return math.sin(angle), math.cos(angle)

    def _observation(self) -> np.ndarray:
        target_q, target_v = self.target_at(self.data.time)
        return np.concatenate([
            self.data.qpos, self.data.qvel, target_q, target_v,
            target_q - self.data.qpos, self.previous_action, self._phase(),
        ]).astype(np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.target_qpos[0]
        self.previous_action.fill(0.0)
        mujoco.mj_forward(self.model, self.data)
        return self._observation(), {"scientific_status": "SOFTWARE_EXPLORATION_ONLY"}

    def desired_human_torque(self) -> np.ndarray:
        target_q, target_v = self.target_at(self.data.time)
        torque = self.kp * (target_q - self.data.qpos) + self.kd * (target_v - self.data.qvel)
        return np.clip(torque, -self.human_limits, self.human_limits)

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=float), -1.0, 1.0)
        exo_torque = self.exo_ranges[:, 0] + 0.5 * (action + 1.0) * (
            self.exo_ranges[:, 1] - self.exo_ranges[:, 0]
        )
        human_torque = self.desired_human_torque()
        self.data.ctrl[self.human_indices] = human_torque
        self.data.ctrl[self.exo_indices] = exo_torque
        mujoco.mj_step(self.model, self.data)
        target_q, _ = self.target_at(self.data.time)
        tracking = float(np.mean((self.data.qpos - target_q) ** 2))
        human_effort = float(np.mean((human_torque / self.human_limits) ** 2))
        exo_effort = float(np.mean(action ** 2))
        smoothness = float(np.mean((action - self.previous_action) ** 2))
        ranges = self.model.jnt_range
        margin = np.minimum(self.data.qpos - ranges[:, 0], ranges[:, 1] - self.data.qpos)
        safety = float(np.mean(np.maximum(0.0, 0.08 - margin) ** 2))
        self.previous_action = action.astype(np.float32)
        reward = -float(np.dot(self.weights, [tracking, human_effort, exo_effort, smoothness, safety]))
        invalid = not math.isfinite(reward) or not np.all(np.isfinite(self.data.qpos))
        terminated = self.data.time >= self.target_time[-1] or invalid
        info = {
            "tracking_mse_rad2": tracking,
            "human_effort_normalized": human_effort,
            "exo_effort_normalized": exo_effort,
            "smoothness": smoothness,
            "safety_penalty": safety,
            "human_torque_nm": human_torque.copy(),
            "exo_torque_nm": exo_torque.copy(),
            "scientific_status": "SOFTWARE_EXPLORATION_ONLY",
        }
        return self._observation(), reward, terminated, False, info
