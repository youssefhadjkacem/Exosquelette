"""Generate passive and active-hybrid exoskeleton prototypes from an arm model."""

from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent
sys.path.insert(0, str(SRC_ROOT))
from pipeline_utils import dump_json, resolve_project_path  # noqa: E402


def values(items) -> str:
    return " ".join(f"{float(item):.9g}" for item in items)


def named(root: ET.Element, tag: str, name: str) -> ET.Element:
    element = root.find(f".//{tag}[@name='{name}']")
    if element is None:
        raise ValueError(f"Element MuJoCo absent: {tag} '{name}'")
    return element


def add_component(root: ET.Element, name: str, config: dict, rgba: list[float], contact: bool) -> None:
    parent = named(root, "body", config["parent_body"])
    if root.find(f".//body[@name='exo_{name}']") is not None:
        raise ValueError(f"Composant deja present: exo_{name}")
    body = ET.SubElement(parent, "body", {"name": f"exo_{name}"})
    ET.SubElement(body, "inertial", {
        "pos": "0 0 0",
        "mass": f"{float(config['mass_kg']):.9g}",
        "diaginertia": values(config["diaginertia_kg_m2"]),
    })
    ET.SubElement(body, "geom", {
        "name": f"exo_{name}_geom",
        "type": "capsule",
        "fromto": values(config["geom_fromto_m"]),
        "size": f"{float(config['geom_radius_m']):.9g}",
        "rgba": values(rgba),
        "contype": "1" if contact else "0",
        "conaffinity": "1" if contact else "0",
        "group": "1",
    })


def build(config: dict, active: bool, output_path: Path) -> ET.ElementTree:
    source = resolve_project_path(config["source_model"])
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(source, parser=parser)
    root = tree.getroot()
    root.set("model", config["model_id"] if active else "light_passive_v1")
    compiler = root.find("compiler")
    if compiler is None:
        compiler = ET.SubElement(root, "compiler")
    compiler.set("meshdir", os.path.relpath(source.parent, output_path.parent).replace("\\", "/"))

    visual = config["visual"]
    for component_name, component in config["components"].items():
        add_component(root, component_name, component, visual["rgba"], visual["contact_enabled"])

    actuator = root.find("actuator")
    if actuator is None:
        actuator = ET.SubElement(root, "actuator")
    for joint_name, joint_config in config["joints"].items():
        joint = named(root, "joint", joint_name)
        base_damping = float(joint.get("damping", "0.05"))
        joint.set("stiffness", f"{float(joint_config['spring_stiffness_nm_per_rad']):.9g}")
        joint.set("springref", f"{float(joint_config['spring_reference_rad']):.9g}")
        joint.set("damping", f"{base_damping + float(joint_config['added_damping_nms_per_rad']):.9g}")
        if active:
            torque_range = joint_config["motor_torque_range_nm"]
            ET.SubElement(actuator, "motor", {
                "name": joint_config["motor_name"],
                "joint": joint_name,
                "gear": "1",
                "ctrllimited": "true",
                "ctrlrange": values(torque_range),
                "forcelimited": "true",
                "forcerange": values(torque_range),
            })
    ET.indent(tree, space="  ")
    return tree


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/exoskeleton/hybrid_active_v1.json")
    args = parser.parse_args(argv)
    try:
        config_path = resolve_project_path(args.config)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        passive_path = resolve_project_path(config["outputs"]["passive"])
        hybrid_path = resolve_project_path(config["outputs"]["hybrid"])
        passive_path.parent.mkdir(parents=True, exist_ok=True)
        build(config, active=False, output_path=passive_path).write(passive_path, encoding="utf-8", xml_declaration=True)
        build(config, active=True, output_path=hybrid_path).write(hybrid_path, encoding="utf-8", xml_declaration=True)
    except (OSError, KeyError, ValueError, ET.ParseError, json.JSONDecodeError) as exc:
        print(f"Generation impossible: {exc}", file=sys.stderr)
        return 2

    metadata = {
        "schema_version": 1,
        "status": config["status"],
        "configuration": str(Path(args.config).as_posix()),
        "source_model": str(Path(config["source_model"]).as_posix()),
        "passive_model": str(Path(config["outputs"]["passive"]).as_posix()),
        "hybrid_model": str(Path(config["outputs"]["hybrid"]).as_posix()),
        "added_mass_kg": sum(float(item["mass_kg"]) for item in config["components"].values()),
        "passive_joints": list(config["joints"]),
        "active_motors": [item["motor_name"] for item in config["joints"].values()],
        "limitations": [
            "ideal rigid alignment with human segments",
            "exploratory spring and motor values",
            "not a manufacturer-validated Light model",
        ],
    }
    dump_json(resolve_project_path(config["outputs"]["metadata"]), metadata)
    print(f"Modele passif: {passive_path}")
    print(f"Modele hybride: {hybrid_path}")
    print(f"Masse ajoutee: {metadata['added_mass_kg']:.3f} kg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
