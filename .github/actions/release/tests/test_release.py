import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import release  # noqa: E402

REPO_URL = "https://github.com/org/repo"


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True)


def commit(message: str) -> None:
    git("commit", "--allow-empty", "--quiet", "--message", message)


@pytest.fixture(autouse=True)
def repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    git("init", "--quiet", "--initial-branch", "main")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.com")
    git("config", "commit.gpgsign", "false")
    git("config", "tag.gpgsign", "false")
    Path("CHANGELOG.md").write_text("# Changelog\n\n## 1.0.0 (2026-01-01)\n\n- feat: first (#1)\n")
    git("add", "CHANGELOG.md")
    commit("Bump version 1.0.0")
    git("tag", "v1.0.0")


def prepare(version: str, breaking_prs: set[str] = frozenset()) -> release.Entry:
    entry = release.build_entry(version, set(breaking_prs), REPO_URL, date="2026-02-01")
    release.prepend_to_changelog(entry)
    return entry


def test_prepend_the_sorted_commits_since_the_last_tag():
    commit("fix: second (#3)")
    commit("feat: first (#2)")

    prepare("1.1.0")

    assert Path("CHANGELOG.md").read_text() == (
        "# Changelog\n"
        "\n"
        "## 1.1.0 (2026-02-01)\n"
        "\n"
        f"- feat: first ([#2]({REPO_URL}/pull/2))\n"
        f"- fix: second ([#3]({REPO_URL}/pull/3))\n"
        "\n"
        "\n"
        "## 1.0.0 (2026-01-01)\n"
        "\n"
        "- feat: first (#1)\n"
    )


def test_merge_commits_are_left_out():
    git("switch", "--quiet", "--create", "feature")
    commit("feat: on a branch (#2)")
    git("switch", "--quiet", "main")
    git("merge", "--no-ff", "--quiet", "--message", "Merge branch feature", "feature")

    entry = prepare("1.1.0")

    assert entry.commits == f"- feat: on a branch ([#2]({REPO_URL}/pull/2))\n"


def test_breaking_changes_come_first_in_bold_with_their_body():
    commit("feat: regular (#2)")
    commit("fix!: drop an option (#3)\n\n- First line\nsecond line (#4)")

    entry = prepare("2.0.0")

    assert entry.commits == (
        f"- **fix!: drop an option ([#3]({REPO_URL}/pull/3))**\n"
        "  - First line\n"
        f"  second line ([#4]({REPO_URL}/pull/4))\n"
        f"- feat: regular ([#2]({REPO_URL}/pull/2))\n"
    )
    assert not entry.breaking_without_major_bump


def test_a_pr_can_be_marked_as_breaking():
    commit("feat(api): change a field (#2)")
    commit("feat!: already breaking (#3)")
    commit("fix: unrelated (#4)")

    entry = prepare("2.0.0", {"2", "3"})

    assert entry.commits == (
        f"- **feat!: already breaking ([#3]({REPO_URL}/pull/3))**\n"
        f"- **feat(api)!: change a field ([#2]({REPO_URL}/pull/2))**\n"
        f"- fix: unrelated ([#4]({REPO_URL}/pull/4))\n"
    )


def test_breaking_changes_without_a_major_bump_are_flagged():
    commit("feat!: breaking (#2)")

    assert prepare("1.1.0").breaking_without_major_bump


def test_refuse_an_existing_tag():
    commit("feat: new (#2)")

    with pytest.raises(release.ReleaseError, match="already exists"):
        prepare("1.0.0")


def test_refuse_a_release_without_new_commits():
    with pytest.raises(release.ReleaseError, match="No new commits"):
        prepare("1.0.1")


def test_refuse_an_invalid_version():
    commit("feat: new (#2)")

    with pytest.raises(release.ReleaseError, match="Invalid version"):
        prepare("v1.1")


def test_update_publiccode_when_the_repository_has_one():
    Path("publiccode.yml").write_text(
        "name: repo\nsoftwareVersion: v1.0.0\nreleaseDate: '2026-01-01'\nurl: x\n"
    )
    commit("feat: new (#2)")

    release.update_publiccode(prepare("1.1.0"))

    assert Path("publiccode.yml").read_text() == (
        "name: repo\nsoftwareVersion: v1.1.0\nreleaseDate: '2026-02-01'\nurl: x\n"
    )


def test_update_publiccode_without_one():
    commit("feat: new (#2)")

    release.update_publiccode(prepare("1.1.0"))

    assert not Path("publiccode.yml").exists()


def open_release_pr(version: str, breaking_prs: set[str] = frozenset()) -> None:
    """Prepare the release on a `release/v<version>` branch, as the prepare action."""
    git("switch", "--quiet", "--create", f"release/v{version}")
    prepare(version, breaking_prs)
    git("add", "CHANGELOG.md")
    commit(f"Bump version {version}")


def merge_main() -> str:
    git("merge", "--no-ff", "--quiet", "--message", "Merge main", "main")
    return subprocess.run(
        ["git", "merge-base", "HEAD", "main"], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_refresh_adds_what_was_merged_on_main_meanwhile():
    commit("fix: before (#2)")
    open_release_pr("1.1.0", {"2"})
    git("switch", "--quiet", "main")
    commit("feat: meanwhile (#3)")
    git("switch", "--quiet", "release/v1.1.0")
    base = merge_main()

    entry = release.refresh_entry("1.1.0", REPO_URL, base)

    assert entry is not None
    assert entry.date == "2026-02-01"
    assert release.release_notes("1.1.0") == (
        f"- **fix!: before ([#2]({REPO_URL}/pull/2))**\n"
        f"- feat: meanwhile ([#3]({REPO_URL}/pull/3))\n"
    )
    assert Path("CHANGELOG.md").read_text().count("## 1.1.0") == 1
    assert release.release_notes("1.0.0") == "- feat: first (#1)\n"


def test_refresh_keeps_a_hand_edited_wording_without_new_prs():
    commit("fix: before (#2)")
    open_release_pr("1.1.0")
    edited = Path("CHANGELOG.md").read_text().replace("fix: before", "fix: reworded")
    Path("CHANGELOG.md").write_text(edited)
    base = merge_main()

    assert release.refresh_entry("1.1.0", REPO_URL, base) is None
    assert Path("CHANGELOG.md").read_text() == edited


def test_release_notes_are_the_section_of_the_version():
    commit("feat: new (#2)")
    prepare("1.1.0")

    assert release.release_notes("1.1.0") == f"- feat: new ([#2]({REPO_URL}/pull/2))\n"
    assert release.release_notes("1.0.0") == "- feat: first (#1)\n"


def test_release_notes_of_a_missing_section():
    with pytest.raises(release.ReleaseError, match="No '## 1.1.0' section"):
        release.release_notes("1.1.0")
