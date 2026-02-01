#!/usr/bin/env zsh
# Zsh completion script for fte (Digital FTE CLI)
#
# Installation:
#   1. Source this file in your ~/.zshrc:
#      source /path/to/fte-completion.zsh
#
#   2. Or install in fpath:
#      cp fte-completion.zsh /usr/local/share/zsh/site-functions/_fte
#      Then reload: compinit
#
# Usage:
#   After installation, type `fte <TAB>` to see available commands
#   Type `fte vault <TAB>` to see vault subcommands, etc.

#compdef fte

# Generate completion using Click's built-in support
_fte_completion() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[fte] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) _FTE_COMPLETE=zsh_complete fte)}")

    for type key descr in ${response}; do
        if [[ "$type" == "plain" ]]; then
            if [[ "$descr" == "_" ]]; then
                completions+=("$key")
            else
                completions_with_descriptions+=("$key":"$descr")
            fi
        elif [[ "$type" == "dir" ]]; then
            _path_files -/
        elif [[ "$type" == "file" ]]; then
            _path_files -f
        fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

# Main completion function with custom argument hints
_fte() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \
        '1: :->command' \
        '*::arg:->args' \
        '--help[Show help message]' \
        '--version[Show version]' \
        '--verbose[Enable verbose logging]' \
        '--quiet[Suppress non-error output]' \
        '--no-color[Disable colored output]'

    case "$state" in
        command)
            local -a commands
            commands=(
                'init:Initialize AI Employee vault'
                'status:Show system status'
                'vault:Vault management commands'
                'watcher:Watcher lifecycle commands'
                'mcp:MCP server management'
                'approval:Approval workflow commands'
                'briefing:CEO briefing commands'
            )
            _describe 'command' commands
            ;;
        args)
            case $line[1] in
                vault)
                    _fte_vault
                    ;;
                watcher)
                    _fte_watcher
                    ;;
                mcp)
                    _fte_mcp
                    ;;
                approval)
                    _fte_approval
                    ;;
                briefing)
                    _fte_briefing
                    ;;
                init|status)
                    _arguments \
                        '--vault-path[Path to vault]:path:_path_files -/' \
                        '--help[Show help message]'
                    ;;
            esac
            ;;
    esac
}

# Vault subcommands
_fte_vault() {
    local -a subcommands
    subcommands=(
        'list:List tasks in folder'
        'create:Create new task'
        'move:Move task between folders'
    )

    if (( CURRENT == 2 )); then
        _describe 'vault command' subcommands
    else
        case $words[2] in
            list)
                if (( CURRENT == 3 )); then
                    _arguments '3:folder:(inbox needs_action done approvals briefings)'
                fi
                _arguments \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--help[Show help message]'
                ;;
            create)
                _arguments \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--task[Task description]:description:' \
                    '--priority[Priority level]:(high medium low)' \
                    '--folder[Target folder]:(inbox needs_action done)' \
                    '--help[Show help message]'
                ;;
            move)
                _arguments \
                    '3:task_file:' \
                    '4:from_folder:(inbox needs_action done approvals briefings)' \
                    '5:to_folder:(inbox needs_action done approvals briefings)' \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--help[Show help message]'
                ;;
        esac
    fi
}

# Watcher subcommands
_fte_watcher() {
    local -a subcommands
    subcommands=(
        'start:Start watcher daemon'
        'stop:Stop watcher daemon'
        'status:Check watcher status'
        'logs:View watcher logs'
    )

    if (( CURRENT == 2 )); then
        _describe 'watcher command' subcommands
    else
        case $words[2] in
            start|stop|logs)
                if (( CURRENT == 3 )); then
                    _arguments '3:watcher:(gmail whatsapp filesystem)'
                fi
                _arguments \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--tail[Number of log lines]:number:' \
                    '--follow[Follow logs in real-time]' \
                    '--help[Show help message]'
                ;;
            status)
                _arguments \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--help[Show help message]'
                ;;
        esac
    fi
}

# MCP subcommands
_fte_mcp() {
    local -a subcommands
    subcommands=(
        'list:List registered MCP servers'
        'add:Add new MCP server'
        'test:Test MCP server health'
        'tools:List available tools'
    )

    if (( CURRENT == 2 )); then
        _describe 'mcp command' subcommands
    else
        case $words[2] in
            list)
                _arguments \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--help[Show help message]'
                ;;
            add)
                _arguments \
                    '3:name:' \
                    '4:url:' \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--auth-file[Authentication file]:file:_path_files' \
                    '--help[Show help message]'
                ;;
            test|tools)
                _arguments \
                    '3:server_name:' \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--timeout[Request timeout]:seconds:' \
                    '--help[Show help message]'
                ;;
        esac
    fi
}

# Approval subcommands
_fte_approval() {
    local -a subcommands
    subcommands=(
        'pending:List pending approvals'
        'review:Review and decide on approval'
    )

    if (( CURRENT == 2 )); then
        _describe 'approval command' subcommands
    else
        case $words[2] in
            pending)
                _arguments \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--help[Show help message]'
                ;;
            review)
                _arguments \
                    '3:approval_id:' \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--help[Show help message]'
                ;;
        esac
    fi
}

# Briefing subcommands
_fte_briefing() {
    local -a subcommands
    subcommands=(
        'generate:Generate CEO briefing report'
        'view:View most recent briefing'
    )

    if (( CURRENT == 2 )); then
        _describe 'briefing command' subcommands
    else
        case $words[2] in
            generate)
                _arguments \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--days[Number of days]:days:' \
                    '--pdf[Generate PDF]' \
                    '--help[Show help message]'
                ;;
            view)
                _arguments \
                    '--vault-path[Path to vault]:path:_path_files -/' \
                    '--help[Show help message]'
                ;;
        esac
    fi
}

# Register completion function
if [[ "$(basename -- ${(%):-%x})" == "_fte" ]]; then
    # Installed as _fte in fpath
    _fte "$@"
else
    # Sourced directly
    compdef _fte fte
fi
