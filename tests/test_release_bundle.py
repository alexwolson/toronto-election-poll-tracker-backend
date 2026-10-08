from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from backend.release_bundle import (
    FORECAST_DRAWS_ASSET,
    FORECAST_DRAWS_RECORD,
    build_backend_release_bundle,
    publish_backend_release,
    verify_forecast_draws,
)
from backend.release_inputs import HISTORICAL_CORPUS_ASSETS, READING_CLASSIFICATION_ASSET


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _upstream_bundles(tmp_path: Path) -> tuple[Path, Path]:
    results = tmp_path / "results"
    polling = tmp_path / "polling"
    results.mkdir(exist_ok=True)
    polling.mkdir(exist_ok=True)
    results_manifest = {
        "repository": "alexwolson/toronto-election-results",
        "source_commit": "b" * 40,
    }
    _write_json(results / "release_manifest.json", results_manifest)
    results_sha = hashlib.sha256((results / "release_manifest.json").read_bytes()).hexdigest()
    _write_json(
        polling / "release_manifest.json",
        {
            "repository": "alexwolson/toronto-election-poll-tracker-data",
            "source_commit": "d" * 40,
            "dependencies": {
                "results": {
                    "repository": "alexwolson/toronto-election-results",
                    "release": "results-test",
                    "source_commit": "b" * 40,
                    "manifest_sha256": results_sha,
                }
            },
        },
    )
    # Every Polling release carries the historical corpus (ADR 0060).
    for name in (*HISTORICAL_CORPUS_ASSETS, READING_CLASSIFICATION_ASSET):
        (polling / name).write_text("id\n", encoding="utf-8")
    return results, polling


CANDIDATES = ("per_chow", "per_brad", "per_alex")
TAG = "backend-2026-09-10.1"


def _processed(
    tmp_path: Path, *, draws: int = 40, ids: tuple[str, ...] = CANDIDATES, rows: int | None = None
) -> Path:
    """Feeds as the snapshot build writes them, plus the final forecast's draws."""
    processed = tmp_path / "processed"
    processed.mkdir()
    feed = {
        "election_cycle_id": "toronto_2026",
        "election_day": {
            "candidates": [{"candidate_id": cid, "display_name": cid.title()} for cid in CANDIDATES]
        },
        "model": {"draws": draws},
    }
    _write_json(processed / "mayoral_forecast.json", feed)
    for filename in ("council_race_cards.json", "trustee_race_cards.json"):
        _write_json(processed / filename, {"feed": filename})
    rng = np.random.default_rng(1)
    shares = rng.dirichlet(np.ones(len(ids) + 1), size=rows or draws)
    np.savez_compressed(
        processed / FORECAST_DRAWS_ASSET,
        candidate_ids=np.asarray(ids),
        full_ballot=shares[:, :-1],
        residual_pool=shares[:, -1],
    )
    return processed


def _build(tmp_path: Path, processed: Path, **overrides) -> Path:
    results, polling = _upstream_bundles(tmp_path)
    arguments = {
        "results_release": "results-test",
        "polling_release": "polling-test",
        "source_commit": "a" * 40,
        "dirty": False,
        "release_tag": TAG,
        "generated_at": "2026-08-27T12:00:00Z",
        **overrides,
    }
    return build_backend_release_bundle(
        processed, results, polling, tmp_path / "project" / "dist", **arguments
    )


def _publication_bundle(tmp_path: Path, head: str, tag: str = TAG) -> tuple[Path, Path]:
    bundle = _build(tmp_path, _processed(tmp_path), source_commit=head, release_tag=tag)
    return bundle.parent, bundle


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
    output = _build(tmp_path, _processed(tmp_path))

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
    processed = _processed(tmp_path)
    (processed / "trustee_race_cards.json").unlink()

    with pytest.raises(FileNotFoundError, match="trustee_race_cards.json"):
        _build(tmp_path, processed)


def test_backend_bundle_carries_the_final_forecast_draws_with_the_feeds_candidates(
    tmp_path: Path,
) -> None:
    output = _build(tmp_path, _processed(tmp_path, draws=40))

    feed = json.loads((output / "mayoral_forecast.json").read_text(encoding="utf-8"))
    record = json.loads((output / FORECAST_DRAWS_RECORD).read_text(encoding="utf-8"))
    named = [c["candidate_id"] for c in feed["election_day"]["candidates"]]
    with np.load(output / FORECAST_DRAWS_ASSET) as arrays:
        assert arrays["candidate_ids"].tolist() == named
        assert arrays["full_ballot"].shape == (40, len(named))
        assert arrays["residual_pool"].shape == (40,)
    assert [c["candidate_id"] for c in record["candidates"]] == named
    assert record["release_tag"] == TAG
    assert record["draws"] == feed["model"]["draws"] == 40
    assert record["npz"] == FORECAST_DRAWS_ASSET
    assert (
        record["npz_sha256"]
        == hashlib.sha256((output / FORECAST_DRAWS_ASSET).read_bytes()).hexdigest()
    )
    assert (
        record["forecast_sha256"]
        == hashlib.sha256((output / "mayoral_forecast.json").read_bytes()).hexdigest()
    )
    manifest = json.loads((output / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["forecast_draws"] == {
        "record": FORECAST_DRAWS_RECORD,
        "draws": FORECAST_DRAWS_ASSET,
    }
    assert {FORECAST_DRAWS_ASSET, FORECAST_DRAWS_RECORD} <= {
        asset["filename"] for asset in manifest["assets"]
    }
    assert verify_forecast_draws(output, tag=TAG) == record


@pytest.mark.parametrize(
    ("processed_options", "message"),
    [
        ({"ids": ("per_brad", "per_chow", "per_alex")}, "candidate ids"),
        ({"ids": ("per_chow", "per_brad")}, "candidate ids"),
        ({"draws": 40, "rows": 39}, "draws"),
    ],
)
def test_backend_bundle_rejects_draws_that_do_not_match_the_feed(
    tmp_path: Path, processed_options: dict, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _build(tmp_path, _processed(tmp_path, **processed_options))


def test_backend_bundle_requires_the_forecast_draws_and_a_valid_tag(tmp_path: Path) -> None:
    processed = _processed(tmp_path)
    with pytest.raises(ValueError, match="backend-YYYY-MM-DD.N"):
        _build(tmp_path, processed, release_tag="backend-latest")
    (processed / FORECAST_DRAWS_ASSET).unlink()
    with pytest.raises(FileNotFoundError, match=FORECAST_DRAWS_ASSET):
        _build(tmp_path, processed)


def test_verify_forecast_draws_detects_truncation_and_corruption(tmp_path: Path) -> None:
    output = _build(tmp_path, _processed(tmp_path))
    with pytest.raises(ValueError, match="release tag"):
        verify_forecast_draws(output, tag="backend-2026-09-10.2")

    record_path = output / FORECAST_DRAWS_RECORD
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record_path.write_text(json.dumps({**record, "draws": 41}), encoding="utf-8")
    with pytest.raises(ValueError, match="draws"):
        verify_forecast_draws(output, tag=TAG)

    record_path.write_text(json.dumps(record), encoding="utf-8")
    data = (output / FORECAST_DRAWS_ASSET).read_bytes()
    (output / FORECAST_DRAWS_ASSET).write_bytes(data[: len(data) // 2])
    with pytest.raises(ValueError, match="sha256"):
        verify_forecast_draws(output, tag=TAG)


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


def test_publish_rejects_draws_recorded_for_another_tag(tmp_path: Path) -> None:
    head = "a" * 40
    project, bundle = _publication_bundle(tmp_path, head, tag="backend-2026-09-10.2")
    calls, runner = _publication_runner(bundle, head)

    with pytest.raises(ValueError, match="release tag"):
        publish_backend_release("backend-2026-09-10.1", bundle, root=project, runner=runner)

    assert not any(command[:3] == ["gh", "release", "create"] for command in calls)
