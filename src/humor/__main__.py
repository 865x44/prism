from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from humor.forge_adapter import AdapterError, adapt_files
from humor.isolation import IsolationError, develop, freeze_candidate
from humor.ioyaml import YamlError, load
from humor.manifest import ManifestError, detect_commits, read_manifest, sha256_file, write_manifest
from humor.review import ReviewError, read_review_file
from humor.versions import CAMPAIGN_PLANNER, FORGE_ADAPTER, HUMOR_DEVELOP, HUMOR_SELECTOR


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for cand in here.parents:
        if (cand / "contracts" / "humor").is_dir():
            return cand
    return here.parents[2]


def _load_candidate(path: Path) -> dict:
    return load(path.read_text(encoding="utf-8"))


def _load_develop(path: Path) -> dict:
    return load(path.read_text(encoding="utf-8"))


def replay(run_dir: Path) -> int:
    source = run_dir / "source.md"
    field = run_dir / "prism-field.json"
    review_path = run_dir / "review.yaml"
    try:
        read_review_file(review_path)
    except ReviewError as exc:
        print(f"review error: {exc}", file=sys.stderr)
        return 1
    for hid in ("H1", "H2"):
        cand_path = run_dir / "candidates" / f"{hid}.yaml"
        freeze_candidate(run_dir, _load_candidate(cand_path))
    sibling = run_dir / "develop-H2.yaml"
    try:
        develop(
            run_dir,
            "H1",
            source_path=source,
            prism_field_path=field,
            extra_inputs=(sibling,),
            develop_payload=_load_develop(run_dir / "develop-H1.yaml"),
        )
        print("isolation error: sibling develop was accepted", file=sys.stderr)
        return 1
    except IsolationError:
        pass
    for hid in ("H1", "H2"):
        develop(
            run_dir,
            hid,
            source_path=source,
            prism_field_path=field,
            extra_inputs=(),
            develop_payload=_load_develop(run_dir / f"develop-{hid}.yaml"),
        )
    refs = []
    for rel in (
        "prism-field.json",
        "source.md",
        "candidates/H1.yaml",
        "candidates/H2.yaml",
        "develop-H1.yaml",
        "develop-H2.yaml",
        "review.yaml",
    ):
        path = run_dir / rel
        refs.append({"path": rel, "sha256": sha256_file(path)})
    prism_commit, forge_commit = detect_commits(_repo_root())
    write_manifest(
        run_dir,
        {
            "run_id": run_dir.name,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_hash": sha256_file(field),
            "prism_commit": prism_commit,
            "forge_commit": forge_commit,
            "prompt_contract_versions": {
                "selector": HUMOR_SELECTOR,
                "develop": HUMOR_DEVELOP,
                "forge_adapter": FORGE_ADAPTER,
                "campaign_planner": CAMPAIGN_PLANNER,
            },
            "model_identity": "fixture",
            "artifact_refs": refs,
            "human_review_status": "REVIEWED",
        },
    )
    print(f"replay ok {run_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="humor")
    sub = parser.add_subparsers(dest="cmd", required=True)
    man = sub.add_parser("manifest")
    man.add_argument("--run-dir", required=True)
    rep = sub.add_parser("replay")
    rep.add_argument("run_dir")
    fs = sub.add_parser("forge-seed")
    fs.add_argument("--candidate", required=True, type=Path)
    fs.add_argument("--develop", required=True, type=Path)
    fs.add_argument("--out", type=Path, default=None)
    fs.add_argument("--title", default=None)
    fs.add_argument("--subtitle", default=None)
    args = parser.parse_args(argv)
    if args.cmd == "manifest":
        run_dir = Path(args.run_dir)
        try:
            data = read_manifest(run_dir)
        except (ManifestError, FileNotFoundError) as exc:
            print(f"manifest error: {exc}", file=sys.stderr)
            return 1
        write_manifest(run_dir, data)
        print(f"ok {run_dir / 'manifest.yaml'}")
        return 0
    if args.cmd == "replay":
        return replay(Path(args.run_dir))
    if args.cmd == "forge-seed":
        try:
            yaml_text = adapt_files(
                args.candidate,
                args.develop,
                out_path=args.out,
                title=args.title,
                subtitle=args.subtitle,
            )
            if not args.out:
                sys.stdout.write(yaml_text)
            return 0
        except (AdapterError, YamlError, OSError, ValueError) as exc:
            print(f"forge-seed error: {exc}", file=sys.stderr)
            return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
