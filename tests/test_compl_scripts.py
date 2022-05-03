EXPECTED_ZSH = r"""#compdef cmd

function _cmd {
local line
_arguments -C \
"1:Commands:((sectionB\:'sectionB subcmd help'))" \
+ '(help)' \
'--help[show help message]' \
'-h[show help message]' \
+ '(optA)' \
'--optA=[AA]: :( )' \
'-a=[AA]: :( )' \
+ '(optB)' \
'--optB=[AB]: :( )' \
+ '(optC)' \
'--optC=[AC]: :( )' \
+ '(optBool)' \
'-optBool[Abool]' \
'+optBool[Abool]' \
'-o[Abool]' \
'+o[Abool]' \
'*::arg:->args'
case $line[1] in
sectionB) _cmd_sectionB ;;
esac
}

function _cmd_sectionB {
_arguments \
+ '(help)' \
'--help[show help message]' \
'-h[show help message]' \
+ '(optA)' \
'--optA=[BA]: :( )' \
+ '(optB)' \
'--optB=[BB]: :( )' \
+ '(optBool)' \
'-optBool[Bbool]' \
'+optBool[Bbool]' \
'-o[Bbool]' \
'+o[Bbool]' \
}
"""


EXPECTED_BASH = """_cmd() {
COMPREPLY=()
local cur=${COMP_WORDS[COMP_CWORD]}

local options="-h --help --optA -a --optB --optC -optBool +optBool -o +o"

local commands="sectionB"
declare -A suboptions
suboptions[sectionB]="-h --help --optA --optB -optBool +optBool -o +o"
if [[ "${COMP_LINE}" == *" sectionB "* ]] ; then
COMPREPLY=( `compgen -W "${suboptions[sectionB]}" -- ${cur}` )
elif [[ ${cur} == -* ]] ; then
COMPREPLY=( `compgen -W "${options}" -- ${cur}`)
else
COMPREPLY=( `compgen -W "${commands}" -- ${cur}`)
fi
}

complete -F _cmd cmd
"""


def test_bash_complete_file(climan, tmp_path):
    script_bash = tmp_path / "cmd.sh"
    climan.bash_complete(script_bash, "cmd")
    produced_bash = script_bash.read_text()
    assert produced_bash == EXPECTED_BASH


def test_zsh_complete_file(climan, tmp_path):
    script_zsh = tmp_path / "_cmd.sh"
    climan.zsh_complete(script_zsh, "cmd", force_grouping=True)
    produced_zsh = script_zsh.read_text()
    assert produced_zsh == EXPECTED_ZSH
