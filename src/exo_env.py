"""Gymnasium environment where RL controls exoskeleton actuators, never human muscles."""

from __future__ import annotations

import math
from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from pipeline_utils import resolve_project_path


def read_opensim_storage(path: Path) -> tuple[list[str], np.ndarray, bool]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    end = next(i for i, line in enumerate(lines) if line.strip().lower() == "endheader")
    header = lines[: end + 1]
    columns = lines[end + 1].split()
    data = np.asarray([[float(value) for value in line.split()] for line in lines[end + 2:] if line.strip()])
    if data.ndim != 2 or data.shape[1] != len(columns):
        raise ValueError(f"Storage OpenSim invalide: {path}")
    in_degrees = any(line.strip().lower() == "indegrees=yes" for line in header)
    return columns, data, in_degrees


class BrasOuvriereEnv(gym.Env):
    """Track an ironing trajectory with independent active-exoskeleton actuators."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        model_path: str | Path,
        target_motion_path: str | Path,
        human_controls_path: str | Path | None = None,
        exo_actuator_prefix: str = "exo_",
        tracking_weight: float = 10.0,
        human_effort_weight: float = 0.1,
        exo_effort_weight: float = 0.01,
        smoothness_weight: float = 0.01,
    ):
        super().__init__()
        self.model_path = resolve_project_path(model_path)
        self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
        self.data = mujoco.MjData(self.model)
        self.joint_names = [
            mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, i)
            for i in range(self.model.njnt)
        ]
        actuator_names = [
            mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i) or f"actuator_{i}"
            for i in range(self.model.nu)
        ]
        self.exo_indices = np.asarray(
            [i for i, name in enumerate(actuator_names) if name.startswith(exo_actuator_prefix)], dtype=int
        )
        self.human_indices = np.asarray(
            [i for i, name in enumerate(actuator_names) if not name.startswith(exo_actuator_prefix)], dtype=int
        )
        if not len(self.exo_indices):
            raise ValueError(
                f"Aucun actionneur '{exo_actuator_prefix}*' dans {self.model_path}. "
                "Ajoutez des moteurs d'exosquelette distincts avant le RL."
            )
        unlimited_actuators = [
            actuator_names[index] for index in self.exo_indices
            if not self.model.actuator_ctrllimited[index]
        ]
        if unlimited_actuators:
            raise ValueError(f"Actionneurs exosquelette sans ctrlrange actif: {', '.join(unlimited_actuators)}")
        unlimited = [name for i, name in enumerate(self.joint_names) if not self.model.jnt_limited[i]]
        if unlimited:
            raise ValueError(f"Limites articulaires MuJoCo desactivees: {', '.join(unlimited)}")

        columns, target, in_degrees = read_opensim_storage(resolve_project_path(target_motion_path))
        self.target_time = target[:, 0]
        self.target_qpos = np.tile(self.model.qpos0, (len(target), 1)).astype(float)
        scalar_joint_types = (mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE)
        for joint_index, joint_name in enumerate(self.joint_names):
            if self.model.jnt_type[joint_index] not in scalar_joint_types:
                raise ValueError(
                    f"Joint MuJoCo non scalaire non pris en charge pour le suivi OpenSim: {joint_name}"
                )
            if joint_name not in columns:
                raise ValueError(f"Trajectoire cible sans coordonnee MuJoCo '{joint_name}'.")
            values = target[:, columns.index(joint_name)]
            qpos_index = self.model.jnt_qposadr[joint_index]
            self.target_qpos[:, qpos_index] = np.radians(values) if in_degrees else values

        self.human_time = self.target_time
        self.human_controls = np.zeros((len(target), len(self.human_indices)), dtype=float)
        if human_controls_path:
            control_columns, controls, _ = read_opensim_storage(resolve_project_path(human_controls_path))
            self.human_time = controls[:, 0]
            for output_index, actuator_index in enumerate(self.human_indices):
                name = actuator_names[actuator_index]
                if name in control_columns:
                    self.human_controls[:, output_index] = controls[:, control_columns.index(name)]

        self.weights = (tracking_weight, human_effort_weight, exo_effort_weight, smoothness_weight)
        self.previous_action = np.zeros(len(self.exo_indices), dtype=np.float32)
        observation_size = self.model.nq + self.model.nv + self.model.nq + self.model.nq
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(observation_size,), dtype=np.float32)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(len(self.exo_indices),), dtype=np.float32)

    def target_at(self, time_s: float) -> np.ndarray:
        return np.asarray([np.interp(time_s, self.target_time, self.target_qpos[:, i]) for i in range(self.model.nq)])

    def _observation(self) -> np.ndarray:
        target = self.target_at(self.data.time)
        return np.concatenate([self.data.qpos, self.data.qvel, target, target - self.data.qpos]).astype(np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = self.target_qpos[0]
        mujoco.mj_forward(self.model, self.data)
        self.previous_action.fill(0)
        return self._observation(), {}

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=float), -1.0, 1.0)
        ranges = self.model.actuator_ctrlrange[self.exo_indices]
        exo_controls = ranges[:, 0] + (action + 1.0) * 0.5 * (ranges[:, 1] - ranges[:, 0])
        self.data.ctrl[self.exo_indices] = exo_controls
        for output_index, actuator_index in enumerate(self.human_indices):
            self.data.ctrl[actuator_index] = np.interp(
                self.data.time, self.human_time, self.human_controls[:, output_index]
            )
        mujoco.mj_step(self.model, self.data)

        target = self.target_at(self.data.time)
        tracking = float(np.mean((self.data.qpos - target) ** 2))
        human_effort = float(np.mean(self.data.ctrl[self.human_indices] ** 2)) if len(self.human_indices) else 0.0
        exo_effort = float(np.mean(action ** 2))
        smoothness = float(np.mean((action - self.previous_action) ** 2))
        self.previous_action = action.astype(np.float32)
        w_track, w_human, w_exo, w_smooth = self.weights
        reward = -(w_track * tracking + w_human * human_effort + w_exo * exo_effort + w_smooth * smoothness)
        terminated = self.data.time >= self.target_time[-1] or not math.isfinite(reward)
        info = {"tracking_mse": tracking, "human_effort": human_effort, "exo_effort": exo_effort, "smoothness": smoothness}
        return self._observation(), float(reward), terminated, False, info


ActiveExoskeletonEnv = BrasOuvriereEnv
