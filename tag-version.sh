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

# Prepare the new changelog entry
NEW_ENTRY="## $VERSION ($DATE)

$COMMITS

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