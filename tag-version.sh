#!/bin/bash

# Script to create a git tag and update CHANGELOG.md
# Usage: ./tag-version.sh <version>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 11.0.1"
    exit 1
fi

VERSION="$1"
DATE=$(date +%Y-%m-%d)

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
if [ -f "CHANGELOG.md" ]; then
    # Insert after the first line (assuming it's a header)
    echo "$NEW_ENTRY" | cat - CHANGELOG.md > CHANGELOG.md.tmp && mv CHANGELOG.md.tmp CHANGELOG.md
else
    # Create new CHANGELOG.md
    echo "# Changelog

$NEW_ENTRY" > CHANGELOG.md
fi

echo "CHANGELOG.md updated with commits from $LAST_TAG to HEAD"

# Create the git tag
git tag -a "v$VERSION" -m "Version $VERSION"

echo "✓ Created tag v$VERSION"
echo "✓ Updated CHANGELOG.md"
echo ""
echo "To push the tag, run: git push origin v$VERSION"