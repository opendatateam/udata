#!/bin/bash

# Script to create a git tag and update CHANGELOG.md
# Usage: ./tag-version.sh <version> [--dry-run]

set -e

DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            VERSION="$1"
            shift
            ;;
    esac
done

if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version> [--dry-run]"
    echo "Example: $0 11.0.1"
    echo "Example: $0 11.0.1 --dry-run"
    exit 1
fi

DATE=$(date +%Y-%m-%d)

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN MODE]"
    echo ""
fi

# Detect main branch (master or main)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if git rev-parse --verify master >/dev/null 2>&1; then
    MAIN_BRANCH="master"
elif git rev-parse --verify main >/dev/null 2>&1; then
    MAIN_BRANCH="main"
else
    echo "Error: Could not detect main branch (neither master nor main exists)"
    exit 1
fi

# Check if we're on the main branch
if [ "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]; then
    echo "Error: You must be on the $MAIN_BRANCH branch to create a release"
    echo "Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Check if working copy is clean
if ! git diff-index --quiet HEAD --; then
    echo "Error: Working copy is not clean. Please commit or stash your changes."
    git status --short
    exit 1
fi

# Check if we're up to date with remote
git fetch origin "$MAIN_BRANCH" --quiet
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "Error: Your local $MAIN_BRANCH branch is not up to date with origin/$MAIN_BRANCH"
    echo "Please run: git pull origin $MAIN_BRANCH"
    exit 1
fi

# Check if tag already exists
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag v$VERSION already exists"
    exit 1
fi

# Get repository URL for PR links
GIT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [[ "$GIT_REMOTE" =~ github.com[:/]([^/]+)/([^/.]+) ]]; then
    REPO_OWNER="${BASH_REMATCH[1]}"
    REPO_NAME="${BASH_REMATCH[2]}"
    REPO_URL="https://github.com/$REPO_OWNER/$REPO_NAME"
else
    REPO_URL=""
fi

# Get the last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

if [ -z "$LAST_TAG" ]; then
    echo "No previous tag found, getting all commits"
    COMMIT_RANGE=""
else
    echo "Getting commits since $LAST_TAG"
    COMMIT_RANGE="$LAST_TAG..HEAD"
fi

# Get commit hashes
if [ -z "$COMMIT_RANGE" ]; then
    COMMIT_HASHES=$(git log --pretty=format:"%H" --no-merges)
else
    COMMIT_HASHES=$(git log "$COMMIT_RANGE" --pretty=format:"%H" --no-merges)
fi

# Check if there are commits
if [ -z "$COMMIT_HASHES" ]; then
    echo "No new commits since last tag"
    exit 1
fi

# Process commits: separate breaking changes and sort
BREAKING_CHANGES=""
REGULAR_COMMITS=""

while IFS= read -r hash; do
    # Get subject and body
    subject=$(git log -1 --pretty=format:"%s" "$hash")
    body=$(git log -1 --pretty=format:"%b" "$hash")

    # Convert PR numbers to links if we have a repo URL
    if [ -n "$REPO_URL" ]; then
        subject=$(echo "$subject" | sed -E "s|#([0-9]+)|[#\1]($REPO_URL/pull/\1)|g")
        body=$(echo "$body" | sed -E "s|#([0-9]+)|[#\1]($REPO_URL/pull/\1)|g")
    fi

    # Check if it's a breaking change (contains ! before :)
    if [[ "$subject" =~ ^[a-z]+(\([^\)]+\))?\!: ]]; then
        # Make subject bold in markdown
        bold_subject=$(echo "- **$subject**")

        # Add body if it exists, indented with two spaces for markdown
        if [ -n "$body" ]; then
            # Indent body lines with two spaces
            indented_body=$(echo "$body" | sed 's/^/  /')
            BREAKING_CHANGES="${BREAKING_CHANGES}${bold_subject}\n${indented_body}\n"
        else
            BREAKING_CHANGES="${BREAKING_CHANGES}${bold_subject}\n"
        fi
    else
        REGULAR_COMMITS="${REGULAR_COMMITS}- ${subject}\n"
    fi
done <<< "$COMMIT_HASHES"

# Sort breaking changes and regular commits alphabetically
if [ -n "$BREAKING_CHANGES" ]; then
    BREAKING_CHANGES=$(echo -e "$BREAKING_CHANGES" | sort)
fi

if [ -n "$REGULAR_COMMITS" ]; then
    REGULAR_COMMITS=$(echo -e "$REGULAR_COMMITS" | sort)
fi

# Combine: breaking changes first, then regular commits
SORTED_COMMITS=""
if [ -n "$BREAKING_CHANGES" ]; then
    SORTED_COMMITS="$BREAKING_CHANGES"
fi
if [ -n "$REGULAR_COMMITS" ]; then
    SORTED_COMMITS="${SORTED_COMMITS}${REGULAR_COMMITS}"
fi

# Prepare the new changelog entry
NEW_ENTRY="## $VERSION ($DATE)
$SORTED_COMMITS
"

# Update CHANGELOG.md
if [ "$DRY_RUN" = true ]; then
    echo "Would update CHANGELOG.md with:"
    echo "$NEW_ENTRY"
    echo "Would run: git add CHANGELOG.md"
    echo "Would run: git commit -m \"Bump version $VERSION\""
    echo "Would run: git tag -a \"v$VERSION\" -m \"Version $VERSION\""
    echo "Would run: git push origin HEAD v$VERSION"
    exit 0
fi

if [ -f "CHANGELOG.md" ]; then
    # Keep existing entries (skip the first line "# Changelog")
    EXISTING_ENTRIES=$(tail -n +2 CHANGELOG.md)
    echo "# Changelog

$NEW_ENTRY$EXISTING_ENTRIES" > CHANGELOG.md
else
    # Create new CHANGELOG.md
    echo "# Changelog

$NEW_ENTRY" > CHANGELOG.md
fi

echo "CHANGELOG.md updated with commits from $LAST_TAG to HEAD"

# Commit the CHANGELOG update
git add CHANGELOG.md
git commit -m "Bump version $VERSION"

echo "✓ Committed CHANGELOG.md"

# Create the git tag
git tag -a "v$VERSION" -m "Version $VERSION"

echo "✓ Created tag v$VERSION"

# Push the commit and tag
git push origin HEAD "v$VERSION"

echo "✓ Pushed commit and tag v$VERSION to origin"