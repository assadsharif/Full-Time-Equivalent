#!/usr/bin/env bash
# Bash completion script for fte (Digital FTE CLI)
#
# Installation:
#   1. Source this file in your ~/.bashrc:
#      source /path/to/fte-completion.bash
#
#   2. Or install system-wide:
#      sudo cp fte-completion.bash /etc/bash_completion.d/fte
#
# Usage:
#   After installation, type `fte <TAB>` to see available commands
#   Type `fte vault <TAB>` to see vault subcommands, etc.

# Generate completion using Click's built-in support
_fte_completion() {
    local IFS=$'\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _FTE_COMPLETE=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done

    return 0
}

# Register completion function
complete -F _fte_completion -o nosort fte

# Completion hints (for better UX)
# These are suggested completions for common arguments

_fte_vault_folders() {
    echo "inbox needs_action done approvals briefings"
}

_fte_watcher_names() {
    echo "gmail whatsapp filesystem"
}

_fte_priority_levels() {
    echo "high medium low"
}
