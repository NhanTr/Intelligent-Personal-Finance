import json

import pytest

from scripts.ci.branch_policy import main, validate_pr


REPOSITORY = "NhanTr/Intelligent-Personal-Finance"


def validate(base, head, head_repository=REPOSITORY, base_repository=REPOSITORY):
    validate_pr(base=base, head=head, base_repository=base_repository,
                head_repository=head_repository, repository=REPOSITORY)


@pytest.mark.parametrize("head", [
    "feat/khoa-k2-import-csv", "feat/nhan-n3-model-evaluation",
    "feat/duy-d2-dashboard", "fix/khoa-k3-model-loader-20261126-140000",
    "docs/nhan-n4-model-card", "chore/khoa-repo-workflow-20261126-140528",
    "refactor/duy-d4-dashboard", "test/khoa-k4-permissions",
])
def test_work_branches_target_develop(head):
    validate("develop", head)


@pytest.mark.parametrize("base,head", [
    ("develop", "main"), ("develop", "develop"),
    ("develop", "feat/khoa-import-csv"), ("develop", "feat/khoa-n2-import-csv"),
    ("develop", "feat/unknown-k2-import-csv"), ("develop", "feat/khoa-k2-CSV"),
    ("develop", "feat/khoa-k2-csv/extra"), ("develop", "feat/khoa-k2-csv\n"),
    ("main", "feat/khoa-k2-import-csv"), ("main", "release/v1"),
    ("other", "feat/khoa-k2-import-csv"),
])
def test_invalid_names_and_routes_are_rejected(base, head):
    with pytest.raises(ValueError):
        validate(base, head)


@pytest.mark.parametrize("base,head", [
    ("main", "develop"), ("develop", "feat/khoa-k2-import-csv"),
])
@pytest.mark.parametrize("source", ["someone/Intelligent-Personal-Finance", ""])
def test_forks_and_deleted_source_repository_are_rejected(base, head, source):
    with pytest.raises(ValueError):
        validate(base, head, head_repository=source)


def test_only_own_develop_can_release_into_own_main():
    validate("main", "develop")
    with pytest.raises(ValueError):
        validate("main", "develop", base_repository="someone/other")


def test_edited_pr_uses_current_base_from_event_and_fails_after_retarget(tmp_path):
    event_path = tmp_path / "event.json"
    event = {
        "action": "edited",
        "pull_request": {
            "base": {"ref": "develop", "repo": {"full_name": REPOSITORY}},
            "head": {"ref": "feat/khoa-k2-import-csv", "repo": {"full_name": REPOSITORY}},
        },
    }
    args = ["--event-path", str(event_path), "--repository", REPOSITORY]
    event_path.write_text(json.dumps(event), encoding="utf-8")
    assert main(args) == 0
    event["pull_request"]["base"]["ref"] = "main"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    assert main(args) == 1


def test_cli_returns_nonzero_for_missing_pr_metadata(tmp_path):
    event_path = tmp_path / "event.json"
    event_path.write_text("{}", encoding="utf-8")
    assert main(["--event-path", str(event_path), "--repository", REPOSITORY]) == 1
