export VIRTUAL_ENV_DISABLE_PROMPT=1

parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}

# Function to get virtual env name
parse_venv() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "($(basename $VIRTUAL_ENV))"
    fi
}

# Combine them in the prompt
#export PS1='\[\e[32m\]$(parse_venv)\[\e[0m\]\[\e[34m\]$(parse_git_branch)\[\e[0m\] \W $ '
#export PS1='\[\e[32m\]$(parse_venv)\[\e[0m\]\[\e[34m\]$(parse_git_branch)\[\e[0m\] \W $ '

export PS1='\[\e[36m\]\u@\h\[\e[0m\] \[\e[32m\]$(parse_venv)\[\e[0m\]\[\e[34m\]$(parse_git_branch)\[\e[0m\] \W <\!>\$ '
export PS1='\[\e[36m\]\u@\h\[\e[0m\] \[\e[32m\]$(parse_venv)\[\e[0m\]\[\e[34m\]$(parse_git_branch)\[\e[0m\] \W <\!>\$ '

alias a=alias
a sdis='xrandr --output  DP-2-1 --rotation normal --mode 1920x1080   --pos 0x0 --output  DP-2-2 --rotation normal --mode 1920x1080  --pos 1920x0 --output eDP-1 --primary  --mode 1280x720 --pos 3840x400 --rotation normal'
a sprompt="export PS1='\[\e[36m\]\u@\h\[\e[0m\] \[\e[32m\]$(parse_venv)\[\e[0m\]\[\e[34m\]$(parse_git_branch)\[\e[0m\] \W <\!>\$ '"

a sba='. ~/.bash_aliases'
a nba='nano ~/.bash_aliases'

a h='history'
a h1='history 15'
a hg='history | grep'

a ga='git add'
a gc='git commit'
a gs='git status'
a gu='git restore --staged' # unstage
a gpsh='git push'
a gl='git log --oneline --decorate --graph --all'
a gpul='git pull'
a grph='git rev-parse --short HEAD'

a gpr='gh pr create' 

a ave='. .venv/bin/activate'

a ksc=' . ~/kscreen.sh'
