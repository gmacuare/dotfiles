# TARGET=~/.zshrc            
# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
#ZSH_THEME="random"
ZSH_THEME="dracula"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in ~/.oh-my-zsh/themes/
# If set to an empty array, this variable will have no effect.
ZSH_THEME_RANDOM_CANDIDATES=( "dracula" "robbyrussell" "agnoster" )


plugins=(
    autojump
    git
    colored-man-pages
    zsh-syntax-highlighting
    zsh-autosuggestions
)

# CUSTOM EXPORTS
# Path to your oh-my-zsh installation.
export ZSH="/home/macuared/.oh-my-zsh"

# Export my locale settings
export LC_ALL=en_GB.UTF-8  
export LANG=en_GB.UTF-8

# To fix issue with zsh auto-suggestion inside Tmux
# https://github.com/zsh-users/zsh-autosuggestions/issues/229
export TERM=xterm-256color

# To source virtualenv
export PATH=~/.local/bin:$PATH

# For TLDR
export PATH=$PATH:~/bin

# For using ctrl+shift+e Vscode
# https://forum.manjaro.org/t/i-want-ibus-daemon-to-run-all-the-time/105414/3
# https://github.com/microsoft/vscode/issues/48480#issuecomment-414181802
export GTK_IM_MODULE="xim"
ibus-daemon -drx


# OTHERS
# Dracula theme specific config.
DRACULA_DISPLAY_CONTEXT=1
DRACULA_DISPLAY_TIME=1

# To avoid ssh-add "Could not open a connection to your authentication agent"
# https://coderwall.com/p/rdi_wq/fix-could-not-open-a-connection-to-your-authentication-agent-when-using-ssh-add
eval $(ssh-agent)


# Remap Caps to Esc for VIM
setxkbmap -option caps:swapescape

# SOURCING FILES
# Source custom aliases
source $HOME/.aliases

# Source oh-my-zsh by default
source $ZSH/oh-my-zsh.sh
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Source autojump
[[ -s /home/macuared/.autojump/etc/profile.d/autojump.sh ]] && source /home/macuared/.autojump/etc/profile.d/autojump.sh
autoload -U compinit && compinit -u

# FUNCTIONS
# To use Chromaterm for ssh sessions
ssh() {
     /usr/bin/ssh "$@" | ct; 
}

