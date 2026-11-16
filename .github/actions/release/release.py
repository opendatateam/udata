"""Changelog generation and parsing shared by the release actions.

Standard library only: the actions run it with the runner's python3, before
any project dependency is installed.
"""

import argparse
import datetime
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

CHANGELOG = Path("CHANGELOG.md")
CHANGELOG_TITLE = "# Changelog"
PUBLICCODE = Path("publiccode.yml")
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
BREAKING_SUBJECT = re.compile(r"^[a-z]+(\([^)]+\))?!: ")
CONVENTIONAL_PREFIX = re.compile(r"^([a-z]+(\([^)]+\))?): ")
PR_REFERENCE = re.compile(r"#(\d+)")


class ReleaseError(Exception):
    pass


@dataclass
class Commit:
    subject: str
    body: str


@dataclass
class Entry:
    version: str
    date: str
    commits: str
    breaking_without_major_bump: bool

    @property
    def section(self) -> str:
        return f"## {self.version} ({self.date})\n\n{self.commits}"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def last_tag(ref: str) -> str | None:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", ref], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def commits_since(tag: str | None, ref: str) -> list[Commit]:
    revision_range = f"{tag}..{ref}" if tag else ref
    hashes = git("log", revision_range, "--no-merges", "--format=%H").split()
    return [
        Commit(
            subject=git("log", "-1", "--format=%s", sha).strip(),
            body=git("log", "-1", "--format=%b", sha).rstrip("\n"),
        )
        for sha in hashes
    ]


@dataclass
class ChangelogItem:
    subject: str
    text: str
    breaking: bool


def changelog_items(
    commits: list[Commit], repo_url: str, breaking_prs: set[str]
) -> list[ChangelogItem]:
    """Breaking changes first (in bold, with their body), then the other commits."""

    def link(text: str) -> str:
        return PR_REFERENCE.sub(rf"[#\1]({repo_url}/pull/\1)", text)

    items = []
    for commit in commits:
        subject = commit.subject
        if breaking_prs & set(re.findall(r"\(#(\d+)\)", subject)):
            # A subject already marked with `!` does not match the prefix and stays as is
            subject = CONVENTIONAL_PREFIX.sub(r"\1!: ", subject, count=1)
        if BREAKING_SUBJECT.match(subject):
            text = f"- **{link(subject)}**"
            if commit.body:
                text += "\n" + "\n".join(f"  {line}" for line in link(commit.body).split("\n"))
            items.append(ChangelogItem(subject, text, breaking=True))
        else:
            items.append(ChangelogItem(subject, f"- {link(subject)}", breaking=False))
    return sorted(items, key=lambda item: (not item.breaking, item.subject))


def build_entry(
    version: str, breaking_prs: set[str], repo_url: str, date: str, ref: str = "HEAD"
) -> Entry:
    """Changelog entry of the commits between the last tag and `ref`."""
    match = VERSION_PATTERN.match(version)
    if not match:
        raise ReleaseError(f"Invalid version '{version}', expected MAJOR.MINOR.PATCH")
    if git("tag", "--list", f"v{version}").strip():
        raise ReleaseError(f"Tag v{version} already exists")

    tag = last_tag(ref)
    commits = commits_since(tag, ref)
    if not commits:
        raise ReleaseError(f"No new commits since {tag}")

    items = changelog_items(commits, repo_url, breaking_prs)
    same_major = tag is not None and tag.lstrip("v").split(".")[0] == match.group(1)
    return Entry(
        version=version,
        date=date,
        commits="\n".join(item.text for item in items) + "\n",
        breaking_without_major_bump=same_major and any(item.breaking for item in items),
    )


def prepend_to_changelog(entry: Entry) -> None:
    previous = CHANGELOG.read_text() if CHANGELOG.exists() else CHANGELOG_TITLE + "\n"
    if not previous.startswith(CHANGELOG_TITLE + "\n"):
        raise ReleaseError(f"{CHANGELOG} does not start with '{CHANGELOG_TITLE}'")
    rest = previous.removeprefix(CHANGELOG_TITLE + "\n").lstrip("\n")
    separator = "\n\n" if rest else ""
    CHANGELOG.write_text(f"{CHANGELOG_TITLE}\n\n{entry.section}{separator}{rest}")


def section_lines(lines: list[str], version: str) -> range:
    """Indices of the `## <version>` section, heading included."""
    heading = re.compile(rf"^## {re.escape(version)}( \(.*\))?$")
    start = next((i for i, line in enumerate(lines) if heading.match(line)), None)
    if start is None:
        raise ReleaseError(f"No '## {version}' section in {CHANGELOG}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return range(start, end)


def release_notes(version: str) -> str:
    """Return the body of the `## <version>` section of the changelog."""
    lines = CHANGELOG.read_text().split("\n")
    section = section_lines(lines, version)
    notes = "\n".join(lines[section.start + 1 : section.stop]).strip("\n")
    if not notes:
        raise ReleaseError(f"The '## {version}' section of {CHANGELOG} is empty")
    return notes + "\n"


def item_prs(lines: list[str]) -> set[str]:
    """PR numbers linked from the first line of the changelog items."""
    return {pr for line in lines if line.startswith("- ") for pr in re.findall(r"\[#(\d+)\]", line)}


def refresh_entry(version: str, repo_url: str, ref: str) -> Entry | None:
    """Regenerate the `## <version>` section from the commits up to `ref`.

    Nothing changes while the section lists the same PRs, so that a push which
    only edits the wording of the release PR keeps its edits. The section keeps
    its date, and the PRs it shows as breaking stay breaking: this is where the
    PRs marked with the `breaking` input of the preparation, or put in bold by
    hand in the release PR, are remembered.
    """
    lines = CHANGELOG.read_text().split("\n")
    section = section_lines(lines, version)
    date = re.search(r"\((.*)\)$", lines[section.start])
    if date is None:
        raise ReleaseError(f"The '## {version}' heading of {CHANGELOG} has no date")
    current = lines[section.start + 1 : section.stop]
    breaking_prs = item_prs([line for line in current if line.startswith("- **")])

    entry = build_entry(version, breaking_prs, repo_url, date.group(1), ref)
    if item_prs(entry.commits.split("\n")) == item_prs(current):
        return None
    CHANGELOG.write_text("\n".join(lines[: section.start] + lines[section.stop :]))
    prepend_to_changelog(entry)
    return entry


def write_pr_body(entry: Entry, path: str) -> None:
    body = entry.commits
    if entry.breaking_without_major_bump:
        warning = "This release contains breaking changes but does not bump the major version."
        print(f"::warning::{warning}")
        body = f"> [!WARNING]\n> {warning}\n\n{body}"
    Path(path).write_text(body)


def repository_url() -> str:
    return f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"


def update_publiccode(entry: Entry) -> None:
    if not PUBLICCODE.exists():
        return
    text = PUBLICCODE.read_text()
    text = re.sub(r"(?m)^softwareVersion: .*$", f"softwareVersion: v{entry.version}", text)
    text = re.sub(r"(?m)^releaseDate: .*$", f"releaseDate: '{entry.date}'", text)
    PUBLICCODE.write_text(text)


def prepare(args: argparse.Namespace) -> None:
    breaking_prs = {pr.strip().lstrip("#") for pr in args.breaking.split(",") if pr.strip()}
    entry = build_entry(
        args.version, breaking_prs, repository_url(), date=datetime.date.today().isoformat()
    )
    prepend_to_changelog(entry)
    update_publiccode(entry)
    write_pr_body(entry, args.body_file)


def refresh(args: argparse.Namespace) -> None:
    entry = refresh_entry(args.version, repository_url(), args.ref)
    if entry is None:
        print(f"The changelog of {args.version} already lists the PRs up to {args.ref}")
    else:
        write_pr_body(entry, args.body_file)


def notes(args: argparse.Namespace) -> None:
    Path(args.output).write_text(release_notes(args.version))


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(required=True)

    prepare_parser = commands.add_parser("prepare", help="Add the release section to the changelog")
    prepare_parser.add_argument("version")
    prepare_parser.add_argument("--breaking", default="", help="Comma separated PR numbers")
    prepare_parser.add_argument("--body-file", required=True, help="Where to write the PR body")
    prepare_parser.set_defaults(func=prepare)

    refresh_parser = commands.add_parser(
        "refresh", help="Regenerate the release section from the commits up to a ref"
    )
    refresh_parser.add_argument("version")
    refresh_parser.add_argument("--ref", required=True, help="Last commit of the release")
    refresh_parser.add_argument("--body-file", required=True, help="Where to write the PR body")
    refresh_parser.set_defaults(func=refresh)

    notes_parser = commands.add_parser("notes", help="Extract the release notes of a version")
    notes_parser.add_argument("version")
    notes_parser.add_argument("--output", required=True)
    notes_parser.set_defaults(func=notes)

    args = parser.parse_args()
    try:
        args.func(args)
    except ReleaseError as error:
        print(f"::error::{error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
