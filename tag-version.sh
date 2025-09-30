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
    COMMITS=$(git log --pretty=format:"- %s" --no-merges)
else
    echo "Getting commits since $LAST_TAG"
    COMMITS=$(git log "$LAST_TAG"..HEAD --pretty=format:"- %s" --no-merges)
fi

# Check if there are commits
if [ -z "$COMMITS" ]; then
    echo "No new commits since last tag"
    exit 1
fi

# Process commits: separate breaking changes and sort
BREAKING_CHANGES=""
REGULAR_COMMITS=""

while IFS= read -r commit; do
    # Convert PR numbers to links if we have a repo URL
    if [ -n "$REPO_URL" ]; then
        commit=$(echo "$commit" | sed -E "s/#([0-9]+)/[#\1]($REPO_URL\/pull\/\1)/g")
    fi

    # Check if it's a breaking change (contains ! before :)
    if [[ "$commit" =~ ^-\ [a-z]+(\([^)]+\))?!: ]]; then
        # Make it bold in markdown
        bold_commit=$(echo "$commit" | sed 's/^- \(.*\)$/- **\1**/')
        BREAKING_CHANGES="${BREAKING_CHANGES}${bold_commit}\n"
    else
        REGULAR_COMMITS="${REGULAR_COMMITS}${commit}\n"
    fi
done <<< "$COMMITS"

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
    echo "Would run: git commit -m \"Update CHANGELOG for version $VERSION\""
    echo "Would run: git tag -a \"v$VERSION\" -m \"Version $VERSION\""
    echo "Would run: git push origin HEAD v$VERSION"
else
    if [ -f "CHANGELOG.md" ]; then
        # Insert after the first line (assuming it's a header)
        echo "$NEW_ENTRY" | cat - CHANGELOG.md > CHANGELOG.md.tmp && mv CHANGELOG.md.tmp CHANGELOG.md
    else
        # Create new CHANGELOG.md
        echo "# Changelog

$NEW_ENTRY" > CHANGELOG.md
    fi

    echo "CHANGELOG.md updated with commits from $LAST_TAG to HEAD"

    # Commit the CHANGELOG update
    git add CHANGELOG.md
    git commit -m "Update CHANGELOG for version $VERSION"

    echo "✓ Committed CHANGELOG.md"

    # Create the git tag
    git tag -a "v$VERSION" -m "Version $VERSION"

    echo "✓ Created tag v$VERSION"

    # Push the commit and tag
    git push origin HEAD "v$VERSION"

    echo "✓ Pushed commit and tag v$VERSION to origin"
fi