---
name: pr-description
description: Analyze git diff between current branch and a reference branch (main/staging), and generate a well-structured, reviewer-friendly PR description in markdown format.
---

# PR Description Generator

Analyze changes between the current branch and a reference branch, then generate a coherent, well-formatted pull request description that highlights important changes and guides reviewers.

## When to Use

- User asks to write or generate a PR description
- User wants to summarize branch changes for a pull request
- User is preparing to merge a feature branch into main/staging
- User asks "what changed in this branch?" with intent to create a PR
- User mentions "PR", "pull request", "merge request", or "code review"

## Instructions

### 1. Clarify Parameters

Determine:
- **Reference branch**: Which branch to compare against? (default: `main`, common alternatives: `staging`, `develop`)
- **Current branch**: Confirm the current branch name
- **PR type**: Feature, bugfix, refactor, chore, or mixed?
- **Target audience**: Internal team, open source, or specific reviewers?

If the reference branch is unclear, ask the user before proceeding.

### 2. Gather Branch Context

Get branch information:

```bash
# Current branch name
git branch --show-current

# Ensure we have latest refs
git fetch origin

# Check if reference branch exists
git rev-parse --verify origin/main 2>/dev/null || git rev-parse --verify main
```

### 3. Analyze the Diff

#### Step A: Get High-Level Statistics

```bash
# Summary of changes
git diff origin/<reference-branch>...HEAD --stat

# Number of commits
git rev-list --count origin/<reference-branch>..HEAD

# List of commits (for context)
git log origin/<reference-branch>..HEAD --oneline --no-merges
```

#### Step B: Identify Changed Files by Category

```bash
# All changed files
git diff origin/<reference-branch>...HEAD --name-only

# Files by change type
git diff origin/<reference-branch>...HEAD --name-status
```

Categorize changes into:
- **Core logic**: Source files with business logic changes
- **Tests**: New or modified test files
- **Configuration**: Config files, CI/CD, build scripts
- **Documentation**: README, docs, comments
- **Dependencies**: package.json, requirements.txt, etc.

#### Step C: Analyze Key Changes

For significant files (large diffs or critical paths):

```bash
# View specific file diff
git diff origin/<reference-branch>...HEAD -- <file-path>

# Show function-level changes (if supported)
git diff origin/<reference-branch>...HEAD --function-context -- <file-path>
```

Focus on:
- New files (especially new modules/classes)
- Deleted files (breaking changes?)
- Files with large line changes
- Files in critical paths (auth, payments, core business logic)

### 4. Identify Key Themes

Group changes into coherent themes:

1. **Primary feature/fix**: What's the main purpose of this PR?
2. **Supporting changes**: What else was modified to support the main change?
3. **Refactoring**: Any code improvements made along the way?
4. **Cleanup**: Dead code removal, formatting, minor fixes?

### 5. Generate PR Description

Structure the description using this template:

```markdown
## Summary

[1-3 sentences describing WHAT this PR does and WHY]

## Key Changes

### [Theme 1: e.g., "New Authentication Flow"]
- [Bullet point describing specific change]
- [Another change in this theme]

### [Theme 2: e.g., "Database Schema Updates"]
- [Changes in this area]

## Files Changed

| Category | Files | Purpose |
|----------|-------|---------|
| Core | `path/to/file.py` | [Brief description] |
| Tests | `tests/test_*.py` | [What's tested] |
| Config | `config.yaml` | [What changed] |

## Review Guide

### What to Focus On
- [Specific file or section that needs careful review]
- [Any complex logic worth double-checking]
- [Potential edge cases to consider]

### What's Safe to Skim
- [Straightforward changes]
- [Auto-generated or boilerplate changes]

## Testing

- [ ] [How this was tested]
- [ ] [Any manual testing steps]

## Breaking Changes

[List any breaking changes, or "None" if backward compatible]

## Related

- Related issue: #[number] (if applicable)
- Related PR: #[number] (if applicable)
- Documentation: [link] (if applicable)
```

### 6. Writing Guidelines

**DO:**
- Lead with the "why" - what problem does this solve?
- Group related changes together
- Highlight files/sections needing careful review
- Mention potential risks or areas of concern
- Include testing evidence
- Keep the summary under 3 sentences
- Write the output as a markdown file in the project root

**DON'T:**
- List every single changed line
- Include implementation details in the summary
- Bury important information in long paragraphs
- Assume the reviewer knows the context
- Skip the "why" and only describe the "what"

### 7. Reviewer-Friendly Tips

To make the reviewer's job easier:

1. **Point out the "scary" parts**: Identify changes that touch critical systems
2. **Explain non-obvious decisions**: Why was X done this way instead of Y?
3. **Call out test coverage**: What's tested, what's not, and why?
4. **Flag dependencies**: Does this PR depend on or block other work?
5. **Suggest review order**: "Start with X, then Y makes more sense"

### 8. Edge Cases

- **Large PRs (50+ files)**: Suggest breaking into smaller PRs, or provide a detailed roadmap
- **Refactoring + Feature**: Clearly separate what's refactoring vs. new functionality
- **Generated code**: Call out auto-generated files that don't need review
- **Merge conflicts**: Note if the branch needs rebasing
- **Draft PRs**: Indicate what's still WIP and what's ready for feedback

### 9. Final Verification

Before presenting the description:

```bash
# Verify diff is accurate
git diff origin/<reference-branch>...HEAD --stat | head -20

# Check for uncommitted changes that might be missing
git status
```

Confirm with user:
- Does the summary capture the intent?
- Are all major changes mentioned?
- Is anything sensitive that shouldn't be in the PR description?

### Common Commands

```bash
# Compare against main
git diff origin/main...HEAD --stat
git log origin/main..HEAD --oneline

# Compare against staging
git diff origin/staging...HEAD --stat
git log origin/staging..HEAD --oneline

# See what files changed
git diff origin/main...HEAD --name-only

# See specific file changes
git diff origin/main...HEAD -- path/to/file.py

# Get commit messages (useful for PR description)
git log origin/main..HEAD --pretty=format:"- %s"
```

### Error Handling

- **Branch doesn't exist**: Suggest alternatives (`main` vs `master`, `staging` vs `develop`)
- **No changes found**: Verify the comparison branches; branch may already be merged
- **Uncommitted changes**: Warn user and ask if they should be included
- **Remote not fetched**: Run `git fetch` and retry
- **Detached HEAD**: Identify the actual branch or commit being compared
