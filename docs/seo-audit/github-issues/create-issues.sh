#!/bin/sh
# Creates the SEO issues in s1mb1o/svoe-vino-lab-dev. Review the drafts first.
set -eu
cd "$(dirname "$0")"
repo=s1mb1o/svoe-vino-lab-dev
: > created.tsv
tail -n +3 SEO-001.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-001.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-001 "$url" | tee -a created.tsv
tail -n +3 SEO-002.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-002.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-002 "$url" | tee -a created.tsv
tail -n +3 SEO-003.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-003.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-003 "$url" | tee -a created.tsv
tail -n +3 SEO-020.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-020.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-020 "$url" | tee -a created.tsv
tail -n +3 SEO-004.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-004.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-004 "$url" | tee -a created.tsv
tail -n +3 SEO-005.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-005.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-005 "$url" | tee -a created.tsv
tail -n +3 SEO-006.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-006.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-006 "$url" | tee -a created.tsv
tail -n +3 SEO-008.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-008.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-008 "$url" | tee -a created.tsv
tail -n +3 SEO-009.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-009.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-009 "$url" | tee -a created.tsv
tail -n +3 SEO-010.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-010.md)" --body-file .body.md --label question --label enhancement) && printf '%s\t%s\n' SEO-010 "$url" | tee -a created.tsv
tail -n +3 SEO-011.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-011.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-011 "$url" | tee -a created.tsv
tail -n +3 SEO-012.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-012.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-012 "$url" | tee -a created.tsv
tail -n +3 SEO-013.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-013.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-013 "$url" | tee -a created.tsv
tail -n +3 SEO-016.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-016.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-016 "$url" | tee -a created.tsv
tail -n +3 SEO-017.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-017.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-017 "$url" | tee -a created.tsv
tail -n +3 SEO-018.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-018.md)" --body-file .body.md --label question) && printf '%s\t%s\n' SEO-018 "$url" | tee -a created.tsv
tail -n +3 SEO-019.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-019.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-019 "$url" | tee -a created.tsv
tail -n +3 SEO-021.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-021.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-021 "$url" | tee -a created.tsv
tail -n +3 SEO-022.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-022.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-022 "$url" | tee -a created.tsv
tail -n +3 SEO-031.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-031.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-031 "$url" | tee -a created.tsv
tail -n +3 SEO-014.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-014.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-014 "$url" | tee -a created.tsv
tail -n +3 SEO-015.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-015.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-015 "$url" | tee -a created.tsv
tail -n +3 SEO-023.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-023.md)" --body-file .body.md --label bug) && printf '%s\t%s\n' SEO-023 "$url" | tee -a created.tsv
tail -n +3 SEO-024.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-024.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-024 "$url" | tee -a created.tsv
tail -n +3 SEO-025.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-025.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-025 "$url" | tee -a created.tsv
tail -n +3 SEO-026.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-026.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-026 "$url" | tee -a created.tsv
tail -n +3 SEO-027.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-027.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-027 "$url" | tee -a created.tsv
tail -n +3 SEO-028.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-028.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-028 "$url" | tee -a created.tsv
tail -n +3 SEO-029.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-029.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-029 "$url" | tee -a created.tsv
tail -n +3 SEO-030.md > .body.md && url=$(gh issue create -R "$repo" --title "$(head -1 SEO-030.md)" --body-file .body.md --label enhancement) && printf '%s\t%s\n' SEO-030 "$url" | tee -a created.tsv
rm -f .body.md
