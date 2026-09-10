from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.release_bundle import build_backend_release_bundle, publish_backend_release


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _upstream_bundles(tmp_path: Path) -> tuple[Path, Path]:
    results = tmp_path / "results"
    polling = tmp_path / "polling"
    results.mkdir()
    polling.mkdir()
    results_manifest = {
        "repository": "alexwolson/toronto-election-results",
        "source_commit": "results-commit",
    }
    _write_json(results / "release_manifest.json", results_manifest)
    results_sha = hashlib.sha256((results / "release_manifest.json").read_bytes()).hexdigest()
    _write_json(
        polling / "release_manifest.json",
        {
            "repository": "alexwolson/toronto-election-poll-tracker-data",
            "source_commit": "polling-commit",
            "dependencies": {
                "results": {
                    "repository": "alexwolson/toronto-election-results",
                    "release": "results-test",
                    "source_commit": "results-commit",
                    "manifest_sha256": results_sha,
                }
            },
        },
    )
    return results, polling


def _publication_bundle(tmp_path: Path, head: str) -> tuple[Path, Path]:
    project = tmp_path / "project"
    bundle = project / "dist"
    bundle.mkdir(parents=True)
    assets = []
    for filename in (
        "mayoral_forecast.json",
        "council_race_cards.json",
        "trustee_race_cards.json",
    ):
        path = bundle / filename
        path.write_text('{"schema_version":1}\n', encoding="utf-8")
        assets.append(
            {"filename": filename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
    manifest = {
        "schema_version": 1,
        "repository": "alexwolson/toronto-election-poll-tracker-backend",
        "source_commit": head,
        "source_dirty": False,
        "dependencies": {
            "results": {
                "repository": "alexwolson/toronto-election-results",
                "release": "results-2026-09-09.2",
                "source_commit": "b" * 40,
                "manifest_sha256": "c" * 64,
            },
            "polling": {
                "repository": "alexwolson/toronto-election-poll-tracker-data",
                "release": "polling-2026-09-09.3",
                "source_commit": "d" * 40,
                "manifest_sha256": "e" * 64,
            },
        },
        "assets": assets,
    }
    (bundle / "release_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return project, bundle


def _publication_runner(
    bundle: Path,
    head: str,
    *,
    remote_head: str | None = None,
    tag_exists: bool = False,
    release_exists: bool = False,
    mutate_download=None,
):
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if command == ["git", "status", "--porcelain"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, stdout=f"{head}\n", stderr="")
        if command == ["git", "ls-remote", "origin", "refs/heads/main"]:
            resolved = remote_head or head
            return subprocess.CompletedProcess(
                command, 0, stdout=f"{resolved}\trefs/heads/main\n", stderr=""
            )
        if command[:4] == ["git", "ls-remote", "--tags", "origin"]:
            output = f"{'f' * 40}\t{command[-1]}\n" if tag_exists else ""
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")
        if command[:3] == ["gh", "release", "view"]:
            if release_exists:
                return subprocess.CompletedProcess(
                    command, 0, stdout='{"tagName":"existing"}\n', stderr=""
                )
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="release not found\n")
        if command[:3] == ["gh", "release", "create"]:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[:3] == ["gh", "release", "download"]:
            destination = Path(command[command.index("--dir") + 1])
            shutil.copytree(bundle, destination, dirs_exist_ok=True)
            if mutate_download:
                mutate_download(destination)
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    return calls, runner


def test_backend_bundle_requires_and_indexes_trustee_cards(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    for filename in (
        "mayoral_forecast.json",
        "council_race_cards.json",
        "trustee_race_cards.json",
    ):
        _write_json(processed / filename, {"feed": filename})
    results, polling = _upstream_bundles(tmp_path)
    output = tmp_path / "dist"

    build_backend_release_bundle(
        processed,
        results,
        polling,
        output,
        results_release="results-test",
        polling_release="polling-test",
        source_commit="backend-commit",
        dirty=False,
        generated_at="2026-08-27T12:00:00Z",
    )

    manifest = json.loads((output / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["feeds"]["trustee_race_cards"] == "trustee_race_cards.json"
    assert (output / "trustee_race_cards.json").is_file()
    trustee_asset = next(
        asset for asset in manifest["assets"] if asset["filename"] == "trustee_race_cards.json"
    )
    assert (
        trustee_asset["sha256"]
        == hashlib.sha256((output / "trustee_race_cards.json").read_bytes()).hexdigest()
    )


def test_backend_bundle_rejects_missing_trustee_cards(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    _write_json(processed / "mayoral_forecast.json", {})
    _write_json(processed / "council_race_cards.json", {})
    results, polling = _upstream_bundles(tmp_path)

    with pytest.raises(FileNotFoundError, match="trustee_race_cards.json"):
        build_backend_release_bundle(
            processed,
            results,
            polling,
            tmp_path / "dist",
            results_release="results-test",
            polling_release="polling-test",
            source_commit="backend-commit",
            dirty=False,
        )


def test_publish_rejects_malformed_tag_before_running_commands(tmp_path: Path) -> None:
    def unexpected_runner(command, **kwargs):
        raise AssertionError(f"should not run {command} with {kwargs}")

    with pytest.raises(ValueError, match="backend-YYYY-MM-DD.N"):
        publish_backend_release(
            "backend-latest", tmp_path / "dist", root=tmp_path, runner=unexpected_runner
        )


def test_publish_targets_remote_main_and_verifies_download(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    head = "a" * 40
    project, bundle = _publication_bundle(tmp_path, head)
    calls, runner = _publication_runner(bundle, head)

    publish_backend_release("backend-2026-09-10.1", bundle, root=project, runner=runner)

    create = next(command for command in calls if command[:3] == ["gh", "release", "create"])
    assert create[create.index("--target") + 1] == head
    assert any(command[:3] == ["gh", "release", "download"] for command in calls)
    assert "published and verified backend release" in capsys.readouterr().out


@pytest.mark.parametrize("existing_kind", ["tag", "release"])
def test_publish_rejects_an_existing_tag_or_release(tmp_path: Path, existing_kind: str) -> None:
    head = "a" * 40
    project, bundle = _publication_bundle(tmp_path, head)
    calls, runner = _publication_runner(
        bundle,
        head,
        tag_exists=existing_kind == "tag",
        release_exists=existing_kind == "release",
    )

    with pytest.raises(RuntimeError, match="already exists"):
        publish_backend_release("backend-2026-09-10.1", bundle, root=project, runner=runner)

    assert not any(command[:3] == ["gh", "release", "create"] for command in calls)


def test_publish_rejects_a_source_commit_other_than_remote_main(tmp_path: Path) -> None:
    head = "a" * 40
    project, bundle = _publication_bundle(tmp_path, head)
    calls, runner = _publication_runner(bundle, head, remote_head="f" * 40)

    with pytest.raises(RuntimeError, match="not the current remote main commit"):
        publish_backend_release("backend-2026-09-10.1", bundle, root=project, runner=runner)

    assert not any(command[:3] == ["gh", "release", "create"] for command in calls)


def test_publish_reports_a_corrupt_download_as_a_consumed_tag(tmp_path: Path) -> None:
    head = "a" * 40
    project, bundle = _publication_bundle(tmp_path, head)

    def corrupt_asset(destination: Path) -> None:
        (destination / "mayoral_forecast.json").write_text("corrupt\n", encoding="utf-8")

    _, runner = _publication_runner(bundle, head, mutate_download=corrupt_asset)

    with pytest.raises(
        RuntimeError,
        match="checksum mismatch.*never reuse this tag",
    ):
        publish_backend_release("backend-2026-09-10.1", bundle, root=project, runner=runner)


@pytest.mark.parametrize("dependency", ["results", "polling"])
def test_publish_verifies_each_downloaded_dependency_pin(tmp_path: Path, dependency: str) -> None:
    head = "a" * 40
    project, bundle = _publication_bundle(tmp_path, head)

    def change_dependency_pin(destination: Path) -> None:
        path = destination / "release_manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["dependencies"][dependency]["release"] = f"{dependency}-2026-09-10.9"
        path.write_text(json.dumps(manifest), encoding="utf-8")

    _, runner = _publication_runner(bundle, head, mutate_download=change_dependency_pin)

    with pytest.raises(
        RuntimeError,
        match="dependency pins changed after upload.*never reuse this tag",
    ):
        publish_backend_release("backend-2026-09-10.1", bundle, root=project, runner=runner)
