#
# ~/.bashrc
#

# Nano is Zenwolf's approachable default editor. Neovim remains available for
# deliberate modal-editor practice, but tools should not select it implicitly.
export EDITOR=nano
export VISUAL=nano
export PATH="$HOME/.local/bin:$PATH"

# If not running interactively, do not configure an interactive shell.
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'

# Keep the familiar command safe: Zenwolf must always enter Hyprland through
# the AMD/Mesa guard so the RTX remains a compute-only device.
start-hyprland() {
    "$HOME/.local/bin/start-zenwolf-desktop" "$@"
}

# Starship only renders the prompt. Bash still owns aliases, history,
# completion, job control, and command execution.
if command -v starship >/dev/null 2>&1; then
    eval "$(starship init bash)"
else
    PS1='[\u@\h \W]\$ '
fi

# A full-width local Ghostty receives the wide welcome screen. Narrow and
# remote shells remain uncluttered.
if [[ -x "$HOME/.local/bin/zenwolf-fastfetch-welcome" ]]; then
    "$HOME/.local/bin/zenwolf-fastfetch-welcome"
fi
