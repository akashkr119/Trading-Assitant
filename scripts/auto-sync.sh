#!/usr/bin/env bash
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS="${TRADING_ASSISTANT_SYNC_INTERVAL:-30}"
LOCK_DIR="/tmp/trading-assistant-auto-sync.lock"
LOG_FILE="${TRADING_ASSISTANT_SYNC_LOG:-/tmp/trading-assistant-auto-sync.log}"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

cd "$REPO_ROOT" || exit 1

log() {
    printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >> "$LOG_FILE"
}

while true; do
    branch="$(git branch --show-current 2>/dev/null || true)"
    if [[ "$branch" != "master" ]]; then
        log "Skipping sync: current branch is '${branch:-detached}', expected master."
    elif ! git diff --quiet || ! git diff --cached --quiet; then
        log "Skipping sync: local uncommitted changes are present."
    elif ! git fetch origin master --quiet; then
        log "Git fetch failed; will retry."
    else
        local_head="$(git rev-parse HEAD 2>/dev/null || true)"
        remote_head="$(git rev-parse origin/master 2>/dev/null || true)"
        if [[ -n "$local_head" && -n "$remote_head" && "$local_head" != "$remote_head" ]]; then
            if git merge-base --is-ancestor "$local_head" "$remote_head"; then
                if git pull --ff-only origin master --quiet; then
                    new_head="$(git rev-parse HEAD 2>/dev/null || true)"
                    log "Updated master: ${local_head:0:12} -> ${new_head:0:12}."

                    if git diff --name-only "$local_head" "$new_head" | grep -Eq '(^|/)(requirements\.txt|pyproject\.toml|uv\.lock|poetry\.lock)$'; then
                        log "Dependency manifest changed; installing project requirements."
                        if python -m pip install -r requirements.txt --disable-pip-version-check --quiet; then
                            log "Dependency installation completed."
                        else
                            log "Dependency installation failed; Streamlit may need manual intervention."
                        fi
                    fi
                else
                    log "Fast-forward pull failed; leaving workspace untouched."
                fi
            else
                log "Skipping sync: local master diverged from origin/master."
            fi
        fi
    fi

    sleep "$INTERVAL_SECONDS"
done
