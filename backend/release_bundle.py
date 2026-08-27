"""Package derived model feeds and pin their exact upstream releases."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from backend.release_inputs import sha256_file, validate_release_chain

REPOSITORY = "alexwolson/toronto-election-poll-tracker-backend"
RESULTS_REPOSITORY = "alexwolson/toronto-election-results"
POLLING_REPOSITORY = "alexwolson/toronto-election-poll-tracker-data"


def _git(*args: str, cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def build_backend_release_bundle(
    processed_dir: str | Path,
    results_bundle: str | Path,
    polling_bundle: str | Path,
    destination: str | Path,
    *,
    results_release: str,
    polling_release: str,
    source_commit: str,
    dirty: bool,
    generated_at: str | None = None,
) -> Path:
    processed = Path(processed_dir)
    results = Path(results_bundle)
    polling = Path(polling_bundle)
    target = Path(destination)
    results_manifest, polling_manifest = validate_release_chain(
        results, polling, results_release=results_release
    )
    names = ("mayoral_forecast.json", "council_race_cards.json", "trustee_race_cards.json")
    for name in names:
        if not (processed / name).is_file():
            raise FileNotFoundError(f"missing backend release feed: {processed / name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{target.name}.stage-", dir=target.parent) as tmp:
        stage = Path(tmp)
        for name in names:
            shutil.copy2(processed / name, stage / name)
        manifest = {
            "schema_version": 1,
            "repository": REPOSITORY,
            "generated_at": generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source_commit": source_commit,
            "source_dirty": dirty,
            "dependencies": {
                "results": {
                    "repository": RESULTS_REPOSITORY,
                    "release": results_release,
                    "source_commit": results_manifest["source_commit"],
                    "manifest_sha256": sha256_file(results / "release_manifest.json"),
                },
                "polling": {
                    "repository": POLLING_REPOSITORY,
                    "release": polling_release,
                    "source_commit": polling_manifest["source_commit"],
                    "manifest_sha256": sha256_file(polling / "release_manifest.json"),
                },
            },
            "feeds": {
                "mayoral_forecast": "mayoral_forecast.json",
                "council_race_cards": "council_race_cards.json",
                "trustee_race_cards": "trustee_race_cards.json",
            },
            "assets": [
                {
                    "filename": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in sorted(stage.iterdir())
            ],
        }
        (stage / "release_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(stage, target)
    return target


def publish_backend_release(tag: str, bundle: str | Path, *, root: str | Path) -> None:
    project = Path(root)
    if _git("status", "--porcelain", cwd=project):
        raise RuntimeError("refusing to publish a backend release from a dirty working tree")
    bundle_path = Path(bundle)
    manifest = json.loads((bundle_path / "release_manifest.json").read_text())
    head = _git("rev-parse", "HEAD", cwd=project)
    if manifest.get("source_dirty") or manifest.get("source_commit") != head:
        raise RuntimeError("release bundle was not built from the current clean commit")
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            REPOSITORY,
            "--title",
            f"Toronto election model {tag}",
            "--generate-notes",
            *sorted(str(path) for path in bundle_path.iterdir() if path.is_file()),
        ],
        cwd=project,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--processed", type=Path, default=Path("data/processed"))
    build.add_argument("--results-bundle", type=Path, required=True)
    build.add_argument("--polling-bundle", type=Path, required=True)
    build.add_argument("--results-release", required=True)
    build.add_argument("--polling-release", required=True)
    build.add_argument("--output", type=Path, default=Path("dist"))
    publish = subparsers.add_parser("publish")
    publish.add_argument("tag")
    publish.add_argument("--bundle", type=Path, default=Path("dist"))
    args = parser.parse_args()
    root = Path.cwd()
    if args.command == "build":
        output = build_backend_release_bundle(
            args.processed,
            args.results_bundle,
            args.polling_bundle,
            args.output,
            results_release=args.results_release,
            polling_release=args.polling_release,
            source_commit=_git("rev-parse", "HEAD", cwd=root),
            dirty=bool(_git("status", "--porcelain", cwd=root)),
        )
        print(f"backend release bundle written to {output}")
    else:
        publish_backend_release(args.tag, args.bundle, root=root)


if __name__ == "__main__":
    main()
