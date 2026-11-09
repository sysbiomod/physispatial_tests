"""Scratch-config helper for the TNFalpha RNG seeding fix (fix/tnfalpha-rng-seeding).

Builds on physispatial_tools/run.py's prepare()/execute(), which already isolates
runs under physispatial_runs/ and never overwrites outputs. This module only adds
the extra XML overrides (max_time, save interval, time_remove_o2) that run.py's
CLI does not expose, so checks 4-6 of the TNFalpha RNG validation can use a short
scratch horizon instead of the shipped 300000-min / 35000-min production config.

Never touches the shipped PhysiCell_settings.xml / .original.xml; all edits are
applied to the per-run copy at <run>/config/run.xml.
"""
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "physispatial_tools"))
import run as run_mod  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_scratch_run(geometry, population, seed, threads, max_time, name, output_root,
                      concentration=1e-7, full_data_interval=20.0, time_remove_o2=1.0,
                      svg_enable=False):
    """Prepare an isolated scratch run with a short horizon, then patch
    overall/max_time, save/full_data/interval, save/SVG/enable and the
    time_remove_o2 user parameter on top of run.py's own overrides."""
    run = run_mod.prepare(geometry, population, diffusion=None, concentration=concentration,
                           seed=seed, threads=threads, output_root=output_root, name=name,
                           smoke_minutes=None)
    config = run / "config" / "run.xml"
    tree = ET.parse(config)
    root = tree.getroot()
    root.find("overall/max_time").text = format(max_time, ".17g")
    root.find("save/full_data/interval").text = format(full_data_interval, ".17g")
    root.find("save/full_data/enable").text = "true"
    svg_node = root.find("save/SVG/enable")
    if svg_node is not None:
        svg_node.text = "true" if svg_enable else "false"
    tro2 = root.find("user_parameters/time_remove_o2")
    if tro2 is not None:
        tro2.text = format(time_remove_o2, ".17g")
    tree.write(config, encoding="utf-8", xml_declaration=True)

    manifest_path = run / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["max_time"] = max_time
    manifest["full_data_interval"] = full_data_interval
    manifest["time_remove_o2"] = time_remove_o2
    manifest["run_xml_sha256"] = sha(config)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return run


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--geometry", default="prism")
    p.add_argument("--population", default="BM0")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--max-time", type=float, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--output-root", default=str(ROOT / "physispatial_runs"))
    p.add_argument("--concentration", type=float, default=1e-7)
    p.add_argument("--full-data-interval", type=float, default=20.0)
    p.add_argument("--time-remove-o2", type=float, default=1.0)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--timeout", type=float)
    a = p.parse_args()
    run = make_scratch_run(a.geometry, a.population, a.seed, a.threads, a.max_time, a.name,
                            a.output_root, a.concentration, a.full_data_interval, a.time_remove_o2)
    print(run, flush=True)
    if a.execute:
        run_mod.execute(run, a.jobs, a.timeout)


if __name__ == "__main__":
    main()
