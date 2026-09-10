"""Package derived model feeds and pin their exact upstream releases."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from backend.release_inputs import sha256_file, validate_release_chain

REPOSITORY = "alexwolson/toronto-election-poll-tracker-backend"
RESULTS_REPOSITORY = "alexwolson/toronto-election-results"
POLLING_REPOSITORY = "alexwolson/toronto-election-poll-tracker-data"
BACKEND_TAG_PATTERN = re.compile(r"^backend-\d{4}-\d{2}-\d{2}\.\d+$")
GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _git(
    *args: str,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    result = runner(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
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


def _validate_dependency_pin(manifest: dict, name: str, repository: str) -> dict:
    dependencies = manifest.get("dependencies")
    pin = dependencies.get(name) if isinstance(dependencies, dict) else None
    if (
        not isinstance(pin, dict)
        or pin.get("repository") != repository
        or not isinstance(pin.get("release"), str)
        or not pin["release"].strip()
        or not GIT_COMMIT_PATTERN.fullmatch(str(pin.get("source_commit", "")))
        or not SHA256_PATTERN.fullmatch(str(pin.get("manifest_sha256", "")))
    ):
        raise RuntimeError(f"backend release manifest has an invalid {name.title()} pin")
    return pin


def _verify_manifest_assets(directory: Path, manifest: dict) -> None:
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise RuntimeError("backend release manifest declares no assets")
    seen: set[str] = set()
    for record in assets:
        if not isinstance(record, dict):
            raise TypeError("backend release manifest has an invalid asset record")
        filename = record.get("filename")
        expected = record.get("sha256")
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or filename in seen
            or not SHA256_PATTERN.fullmatch(str(expected or ""))
        ):
            raise RuntimeError("backend release manifest has an invalid asset record")
        seen.add(filename)
        path = directory / filename
        if not path.is_file():
            raise RuntimeError(f"released asset is missing: {filename}")
        if sha256_file(path) != expected:
            raise RuntimeError(f"released asset checksum mismatch: {filename}")


def _release_exists(
    tag: str,
    *,
    project: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    result = runner(
        ["gh", "release", "view", tag, "--repo", REPOSITORY, "--json", "tagName"],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    error = f"{result.stdout}\n{result.stderr}".lower()
    if "release not found" in error or "http 404" in error:
        return False
    raise RuntimeError(f"could not determine whether release {tag} exists: {error.strip()}")


def _verify_published_release(
    tag: str,
    *,
    project: Path,
    local_manifest_path: Path,
    expected_source_commit: str,
    expected_pins: dict[str, dict],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    with tempfile.TemporaryDirectory(prefix=f"verify-{tag}-") as tmp:
        downloaded = Path(tmp)
        runner(
            [
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                REPOSITORY,
                "--dir",
                str(downloaded),
            ],
            cwd=project,
            check=True,
        )
        manifest_path = downloaded / "release_manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError("published release is missing release_manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_commit") != expected_source_commit:
            raise RuntimeError("published release manifest source commit changed after upload")
        released_pins = {
            "results": _validate_dependency_pin(manifest, "results", RESULTS_REPOSITORY),
            "polling": _validate_dependency_pin(manifest, "polling", POLLING_REPOSITORY),
        }
        if released_pins != expected_pins:
            raise RuntimeError("published release manifest dependency pins changed after upload")
        if manifest_path.read_bytes() != local_manifest_path.read_bytes():
            raise RuntimeError("published release manifest bytes differ from the uploaded bundle")
        _verify_manifest_assets(downloaded, manifest)


def publish_backend_release(
    tag: str,
    bundle: str | Path,
    *,
    root: str | Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    if not BACKEND_TAG_PATTERN.fullmatch(tag):
        raise ValueError(f"backend release tag must match backend-YYYY-MM-DD.N; received {tag!r}")
    project = Path(root)
    if _git("status", "--porcelain", cwd=project, runner=runner):
        raise RuntimeError("refusing to publish a backend release from a dirty working tree")
    bundle_path = Path(bundle)
    if not bundle_path.is_absolute():
        bundle_path = project / bundle_path
    manifest_path = bundle_path / "release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    head = _git("rev-parse", "HEAD", cwd=project, runner=runner)
    if manifest.get("source_dirty") or manifest.get("source_commit") != head:
        raise RuntimeError("release bundle was not built from the current clean commit")
    expected_pins = {
        "results": _validate_dependency_pin(manifest, "results", RESULTS_REPOSITORY),
        "polling": _validate_dependency_pin(manifest, "polling", POLLING_REPOSITORY),
    }
    _verify_manifest_assets(bundle_path, manifest)

    remote_main = _git("ls-remote", "origin", "refs/heads/main", cwd=project, runner=runner).split()
    if not remote_main or not GIT_COMMIT_PATTERN.fullmatch(remote_main[0]):
        raise RuntimeError("could not resolve the remote main commit")
    if head != remote_main[0]:
        raise RuntimeError(
            f"source commit {head} is not the current remote main commit {remote_main[0]}"
        )
    if _git(
        "ls-remote",
        "--tags",
        "origin",
        f"refs/tags/{tag}",
        cwd=project,
        runner=runner,
    ):
        raise RuntimeError(f"remote tag already exists: {tag}")
    if _release_exists(tag, project=project, runner=runner):
        raise RuntimeError(f"GitHub release already exists: {tag}")

    try:
        runner(
            [
                "gh",
                "release",
                "create",
                tag,
                "--repo",
                REPOSITORY,
                "--target",
                head,
                "--title",
                f"Toronto election model {tag}",
                "--generate-notes",
                *sorted(str(path) for path in bundle_path.iterdir() if path.is_file()),
            ],
            cwd=project,
            check=True,
        )
        _verify_published_release(
            tag,
            project=project,
            local_manifest_path=manifest_path,
            expected_source_commit=head,
            expected_pins=expected_pins,
            runner=runner,
        )
    except Exception as error:
        raise RuntimeError(
            f"backend release {tag} failed or could not be verified: {error}. "
            "Inspect the GitHub release and tag, keep any partial publication "
            "immutable, and publish a correction under a new tag; never reuse this tag."
        ) from error
    print(f"published and verified backend release {tag} at source commit {head}")


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
