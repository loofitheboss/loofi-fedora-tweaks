# Bash completion script for loofi-fedora-tweaks CLI
# Source this file in your .bashrc: source /path/to/loofi-fedora-tweaks.bash

_loofi_fedora_tweaks() {
    local cur prev words cword
    _init_completion || return

    local commands="info health disk processes temperature netmon cleanup tweak advanced network doctor hardware plugins support-bundle vm vfio mesh teleport ai-models preset focus-mode security-audit"

    # Subcommand completions
    local cleanup_actions="all dnf journal trim autoremove rpmdb"
    local tweak_actions="power audio battery status"
    local advanced_actions="dnf-tweaks bbr gamemode swappiness"
    local network_actions="dns"
    local plugins_actions="list enable disable"
    local vm_actions="list status start stop"
    local vfio_actions="check gpus plan"
    local mesh_actions="discover status"
    local teleport_actions="capture list restore"
    local ai_models_actions="list recommend"
    local preset_actions="list apply export"
    local focus_mode_actions="on off status"

    # Power profiles
    local power_profiles="performance balanced power-saver"
    local dns_providers="cloudflare google quad9 opendns"
    local sort_options="cpu memory"

    case "${cword}" in
        1)
            COMPREPLY=($(compgen -W "${commands}" -- "${cur}"))
            return 0
            ;;
        2)
            case "${prev}" in
                cleanup)
                    COMPREPLY=($(compgen -W "${cleanup_actions}" -- "${cur}"))
                    return 0
                    ;;
                tweak)
                    COMPREPLY=($(compgen -W "${tweak_actions}" -- "${cur}"))
                    return 0
                    ;;
                advanced)
                    COMPREPLY=($(compgen -W "${advanced_actions}" -- "${cur}"))
                    return 0
                    ;;
                network)
                    COMPREPLY=($(compgen -W "${network_actions}" -- "${cur}"))
                    return 0
                    ;;
                plugins)
                    COMPREPLY=($(compgen -W "${plugins_actions}" -- "${cur}"))
                    return 0
                    ;;
                vm)
                    COMPREPLY=($(compgen -W "${vm_actions}" -- "${cur}"))
                    return 0
                    ;;
                vfio)
                    COMPREPLY=($(compgen -W "${vfio_actions}" -- "${cur}"))
                    return 0
                    ;;
                mesh)
                    COMPREPLY=($(compgen -W "${mesh_actions}" -- "${cur}"))
                    return 0
                    ;;
                teleport)
                    COMPREPLY=($(compgen -W "${teleport_actions}" -- "${cur}"))
                    return 0
                    ;;
                ai-models)
                    COMPREPLY=($(compgen -W "${ai_models_actions}" -- "${cur}"))
                    return 0
                    ;;
                preset)
                    COMPREPLY=($(compgen -W "${preset_actions}" -- "${cur}"))
                    return 0
                    ;;
                focus-mode)
                    COMPREPLY=($(compgen -W "${focus_mode_actions}" -- "${cur}"))
                    return 0
                    ;;
            esac
            ;;
    esac

    # Handle options
    case "${prev}" in
        --profile)
            COMPREPLY=($(compgen -W "${power_profiles}" -- "${cur}"))
            return 0
            ;;
        --provider)
            COMPREPLY=($(compgen -W "${dns_providers}" -- "${cur}"))
            return 0
            ;;
        --sort)
            COMPREPLY=($(compgen -W "${sort_options}" -- "${cur}"))
            return 0
            ;;
        --days|--limit|-n|--count|--value)
            # Numeric arguments - no completion
            return 0
            ;;
        --path)
            # File path completion
            _filedir
            return 0
            ;;
        --target)
            # No specific completion for target
            return 0
            ;;
    esac

    # Global options
    if [[ "${cur}" == -* ]]; then
        local opts="--help --version --json"
        case "${words[1]}" in
            disk)
                opts+=" --details"
                ;;
            processes)
                opts+=" -n --count --sort"
                ;;
            netmon)
                opts+=" --connections"
                ;;
            cleanup)
                opts+=" --days"
                ;;
            tweak)
                opts+=" --profile --limit"
                ;;
            advanced)
                opts+=" --value"
                ;;
            network)
                opts+=" --provider"
                ;;
            teleport)
                opts+=" --path --target"
                ;;
            focus-mode)
                opts+=" --profile"
                ;;
        esac
        COMPREPLY=($(compgen -W "${opts}" -- "${cur}"))
        return 0
    fi

    return 0
}

complete -F _loofi_fedora_tweaks loofi
complete -F _loofi_fedora_tweaks loofi-fedora-tweaks
