#compdef loofi loofi-fedora-tweaks

# Zsh completion script for loofi-fedora-tweaks CLI
# Install: Copy to a directory in your $fpath (e.g., ~/.zsh/completions/)
# Then run: autoload -Uz compinit && compinit

_loofi_fedora_tweaks() {
    local -a commands
    local -a cleanup_actions tweak_actions advanced_actions network_actions
    local -a plugins_actions vm_actions vfio_actions mesh_actions
    local -a teleport_actions ai_models_actions preset_actions focus_mode_actions

    commands=(
        'info:Show system information'
        'health:System health check overview'
        'disk:Disk usage information'
        'processes:Show top processes'
        'temperature:Show temperature readings'
        'netmon:Network interface monitoring'
        'cleanup:System cleanup operations'
        'tweak:Hardware tweaks (power, audio, battery)'
        'advanced:Advanced optimizations'
        'network:Network configuration'
        'doctor:Check system dependencies and diagnostics'
        'hardware:Show detected hardware profile'
        'plugins:Manage plugins'
        'support-bundle:Export support bundle ZIP'
        'vm:Virtual machine management'
        'vfio:GPU passthrough assistant'
        'mesh:Loofi Link mesh networking'
        'teleport:State Teleport workspace capture/restore'
        'ai-models:AI model management'
        'preset:Manage system presets'
        'focus-mode:Focus mode distraction blocking'
        'security-audit:Run security audit and show score'
    )

    cleanup_actions=(
        'all:Run all cleanup operations'
        'dnf:Clean DNF cache'
        'journal:Vacuum system journal'
        'trim:Trim SSD'
        'autoremove:Remove unused packages'
        'rpmdb:Rebuild RPM database'
    )

    tweak_actions=(
        'power:Set power profile'
        'audio:Restart audio service'
        'battery:Set battery charge limit'
        'status:Show current status'
    )

    advanced_actions=(
        'dnf-tweaks:Apply DNF performance tweaks'
        'bbr:Enable TCP BBR congestion control'
        'gamemode:Install GameMode'
        'swappiness:Set swappiness value'
    )

    network_actions=(
        'dns:Configure DNS provider'
    )

    plugins_actions=(
        'list:List installed plugins'
        'enable:Enable a plugin'
        'disable:Disable a plugin'
    )

    vm_actions=(
        'list:List virtual machines'
        'status:Show VM status'
        'start:Start a VM'
        'stop:Stop a VM'
    )

    vfio_actions=(
        'check:Check VFIO prerequisites'
        'gpus:List GPU passthrough candidates'
        'plan:Show step-by-step setup plan'
    )

    mesh_actions=(
        'discover:Discover nearby devices'
        'status:Show mesh network status'
    )

    teleport_actions=(
        'capture:Capture workspace state'
        'list:List saved packages'
        'restore:Restore a package'
    )

    ai_models_actions=(
        'list:List AI models'
        'recommend:Get recommended model'
    )

    preset_actions=(
        'list:List available presets'
        'apply:Apply a preset'
        'export:Export a preset to file'
    )

    focus_mode_actions=(
        'on:Enable focus mode'
        'off:Disable focus mode'
        'status:Show focus mode status'
    )

    _arguments -C \
        '(-h --help)'{-h,--help}'[Show help]' \
        '(-v --version)'{-v,--version}'[Show version]' \
        '--json[Output in JSON format]' \
        '1: :->command' \
        '*:: :->args'

    case $state in
        command)
            _describe -t commands 'loofi command' commands
            ;;
        args)
            case $words[1] in
                cleanup)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'cleanup action' cleanup_actions
                    else
                        _arguments \
                            '--days[Days to keep journal]:days:' \
                            '*::'
                    fi
                    ;;
                tweak)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'tweak action' tweak_actions
                    else
                        _arguments \
                            '--profile[Power profile]:profile:(performance balanced power-saver)' \
                            '--limit[Battery limit]:limit:' \
                            '*::'
                    fi
                    ;;
                advanced)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'advanced action' advanced_actions
                    else
                        _arguments \
                            '--value[Swappiness value]:value:' \
                            '*::'
                    fi
                    ;;
                network)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'network action' network_actions
                    else
                        _arguments \
                            '--provider[DNS provider]:provider:(cloudflare google quad9 opendns)' \
                            '*::'
                    fi
                    ;;
                plugins)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'plugin action' plugins_actions
                    else
                        _arguments '*:plugin name:'
                    fi
                    ;;
                vm)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'vm action' vm_actions
                    else
                        _arguments '*:VM name:'
                    fi
                    ;;
                vfio)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'vfio action' vfio_actions
                    fi
                    ;;
                mesh)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'mesh action' mesh_actions
                    fi
                    ;;
                teleport)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'teleport action' teleport_actions
                    else
                        _arguments \
                            '--path[Workspace path]:path:_files -/' \
                            '--target[Target device]:target:' \
                            '*:package ID:'
                    fi
                    ;;
                ai-models)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'ai-models action' ai_models_actions
                    fi
                    ;;
                preset)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'preset action' preset_actions
                    elif (( CURRENT == 3 )); then
                        _arguments '*:preset name:'
                    elif (( CURRENT == 4 )); then
                        _arguments '*:export path:_files'
                    fi
                    ;;
                focus-mode)
                    if (( CURRENT == 2 )); then
                        _describe -t actions 'focus-mode action' focus_mode_actions
                    else
                        _arguments \
                            '--profile[Focus profile]:profile:' \
                            '*::'
                    fi
                    ;;
                disk)
                    _arguments \
                        '--details[Show large directories]' \
                        '*::'
                    ;;
                processes)
                    _arguments \
                        {-n,--count}'[Number of processes]:count:' \
                        '--sort[Sort by]:sort:(cpu memory)' \
                        '*::'
                    ;;
                netmon)
                    _arguments \
                        '--connections[Show active connections]' \
                        '*::'
                    ;;
            esac
            ;;
    esac
}

_loofi_fedora_tweaks "$@"
