"""Package derived model feeds and pin their exact upstream releases.

A release also carries the final Mayoral Forecast's named-share Election Outcome
Draws (``mayoral_forecast_draws.npz``) and their record
(``mayoral_forecast_draws.json``: release tag, draw count, candidates, the npz's
and the forecast feed's sha256), so one tag pins the forecast and its draws.
"""

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

import numpy as np

from backend.release_inputs import sha256_file, validate_release_chain

REPOSITORY = "alexwolson/toronto-election-poll-tracker-backend"
RESULTS_REPOSITORY = "alexwolson/toronto-election-results"
POLLING_REPOSITORY = "alexwolson/toronto-election-poll-tracker-data"
BACKEND_TAG_PATTERN = re.compile(r"^backend-\d{4}-\d{2}-\d{2}\.\d+$")
GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
FORECAST_FEED = "mayoral_forecast.json"
FORECAST_DRAWS_ASSET = "mayoral_forecast_draws.npz"
FORECAST_DRAWS_RECORD = "mayoral_forecast_draws.json"
DRAWS_ARRAYS = {
    "candidate_ids": "the named candidates, in column order",
    "full_ballot": "draws x named candidates: each one's share of valid votes",
    "residual_pool": "per draw, the share of every other candidate on the ballot; "
    "full_ballot plus residual_pool sums to 1",
}


def _git(
    *args: str,
    cwd: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    result = runner(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _validate_tag(tag: str) -> None:
    if not BACKEND_TAG_PATTERN.fullmatch(tag):
        raise ValueError(f"backend release tag must match backend-YYYY-MM-DD.N; received {tag!r}")


def _check_draws(npz: Path, feed: dict, draws: int) -> None:
    """Fail unless the npz holds exactly ``draws`` coherent draws for the feed's candidates."""
    named = [c["candidate_id"] for c in feed["election_day"]["candidates"]]
    with np.load(npz, allow_pickle=False) as arrays:
        if set(arrays.files) != set(DRAWS_ARRAYS):
            raise ValueError(f"forecast draws hold arrays {sorted(arrays.files)}")
        ids, full, pool = (
            arrays[name] for name in ("candidate_ids", "full_ballot", "residual_pool")
        )
    if ids.tolist() != named:
        raise ValueError(f"forecast draws candidate ids {ids.tolist()} != feed's {named}")
    if full.shape != (draws, len(named)) or pool.shape != (draws,):
        raise ValueError(
            f"forecast draws have shapes {full.shape} and {pool.shape}; expected {draws} draws"
        )
    if not (np.isfinite(full).all() and np.isfinite(pool).all()):
        raise ValueError("forecast draws are not all finite")
    if not np.allclose(full.sum(axis=1) + pool, 1.0, atol=1e-6):
        raise ValueError("forecast draws do not sum to 1")


def verify_forecast_draws(directory: str | Path, *, tag: str) -> dict:
    """Check a bundle's draws against their record and the forecast feed; return the record.

    Catches a record for another tag, a truncated or corrupt npz (sha256, shapes,
    draw count) and draws whose candidates are not the feed's named candidates.
    """
    directory = Path(directory)
    record = json.loads((directory / FORECAST_DRAWS_RECORD).read_text(encoding="utf-8"))
    if record.get("release_tag") != tag:
        raise ValueError(
            f"forecast draws record release tag {record.get('release_tag')!r} != {tag!r}"
        )
    npz = directory / str(record.get("npz"))
    if record.get("npz") != FORECAST_DRAWS_ASSET or not npz.is_file():
        raise ValueError(f"forecast draws record does not name {FORECAST_DRAWS_ASSET}")
    if sha256_file(npz) != record.get("npz_sha256"):
        raise ValueError("forecast draws npz sha256 does not match its record")
    feed_path = directory / FORECAST_FEED
    if sha256_file(feed_path) != record.get("forecast_sha256"):
        raise ValueError("forecast feed sha256 does not match the draws record")
    feed = json.loads(feed_path.read_text(encoding="utf-8"))
    if record.get("draws") != feed["model"]["draws"]:
        raise ValueError(
            f"forecast draws record has {record.get('draws')} draws; the feed has "
            f"{feed['model']['draws']}"
        )
    _check_draws(npz, feed, record["draws"])
    if [c["candidate_id"] for c in record["candidates"]] != [
        c["candidate_id"] for c in feed["election_day"]["candidates"]
    ]:
        raise ValueError("forecast draws record candidate ids differ from the feed")
    return record


def _draws_record(stage: Path, tag: str) -> dict:
    feed = json.loads((stage / FORECAST_FEED).read_text(encoding="utf-8"))
    draws = feed["model"]["draws"]
    _check_draws(stage / FORECAST_DRAWS_ASSET, feed, draws)
    return {
        "release_tag": tag,
        "election_cycle_id": feed["election_cycle_id"],
        "forecast": FORECAST_FEED,
        "forecast_sha256": sha256_file(stage / FORECAST_FEED),
        "candidates": [
            {"candidate_id": c["candidate_id"], "name": c["display_name"]}
            for c in feed["election_day"]["candidates"]
        ],
        "draws": draws,
        "npz": FORECAST_DRAWS_ASSET,
        "npz_sha256": sha256_file(stage / FORECAST_DRAWS_ASSET),
        "arrays": DRAWS_ARRAYS,
    }


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
    release_tag: str,
    generated_at: str | None = None,
) -> Path:
    _validate_tag(release_tag)
    processed = Path(processed_dir)
    results = Path(results_bundle)
    polling = Path(polling_bundle)
    target = Path(destination)
    results_manifest, polling_manifest = validate_release_chain(
        results, polling, results_release=results_release
    )
    names = (FORECAST_FEED, "council_race_cards.json", "trustee_race_cards.json")
    for name in (*names, FORECAST_DRAWS_ASSET):
        if not (processed / name).is_file():
            raise FileNotFoundError(f"missing backend release feed: {processed / name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{target.name}.stage-", dir=target.parent) as tmp:
        stage = Path(tmp)
        for name in (*names, FORECAST_DRAWS_ASSET):
            shutil.copy2(processed / name, stage / name)
        (stage / FORECAST_DRAWS_RECORD).write_text(
            json.dumps(_draws_record(stage, release_tag), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
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
            "forecast_draws": {"record": FORECAST_DRAWS_RECORD, "draws": FORECAST_DRAWS_ASSET},
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
        verify_forecast_draws(downloaded, tag=tag)


def publish_backend_release(
    tag: str,
    bundle: str | Path,
    *,
    root: str | Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    _validate_tag(tag)
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
    verify_forecast_draws(bundle_path, tag=tag)

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
    build.add_argument("--release-tag", required=True, help="the tag this bundle is published as")
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
            release_tag=args.release_tag,
        )
        print(f"backend release bundle written to {output}")
    else:
        publish_backend_release(args.tag, args.bundle, root=root)


if __name__ == "__main__":
    main()
