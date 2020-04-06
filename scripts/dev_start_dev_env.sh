#!/bin/bash



source venv/bin/activate


echo "TERM_PROGRAM : ${TERM_PROGRAM}"


# function tab () {
#   local cmd=""
#   local cdto="$PWD"
#   local args="$@"


#   if [ -d "$1" ]; then
#     cdto=`cd "$1"; pwd`
#     args="${@:2}"
#   fi

#   if [ -n "$args" ]; then
#     cmd="; $args"
#   fi

#   echo "cmd : ${cmd}"
#   echo "cdto : ${cdto}"
#   echo "args : ${args}"



#   if [ $TERM_PROGRAM = "Apple_Terminal" ]; then
#     echo "using : ${TERM_PROGRAM}"

#     osascript 
#       -e "tell application \"Terminal\"" \
#         -e "tell application \"System Events\" to keystroke \"t\" using {command down}" \
#         -e "do script \"cd $cdto; clear $cmd\" in front window" \
#       -e "end tell"
#       > /dev/null
      
#   elif [ $TERM_PROGRAM = "iTerm.app" ]; then
#     echo "using : ${TERM_PROGRAM}"

#     osascript
#       -e "tell application \"iTerm\"" \
#         # -e "tell current terminal" \
#           # -e "launch session \"Default Session\"" \
#           # -e "tell the last session" \
#           -e "tell application \"System Events\" to keystroke \"t\" using command down"
#             -e "tell application \"iTerm\" to tell session -1 of current terminal to write text \"cd \"$cdto\"$cmd\"" \
#           -e "end tell" \
#         -e "end tell" \
#       -e "end tell" \
#       > /dev/null
#   fi
# }

# function new_tab() {
#   CDTO=$1
#   TAB_NAME=$2
#   COMMAND=$3

#   osascript \
#     -e "tell application \"Terminal\"" \
#     -e "tell application \"System Events\" to keystroke \"t\" using {command down}" \
#     -e "do script \"cd $CDTO; clear $cmd\" in front window" \
#     -e "do script \"printf '\\\e]1;$TAB_NAME\\\a'; $COMMAND\" in front window" \
#     -e "end tell" > /dev/null
# }


newtabi(){

  if [ $TERM_PROGRAM = "iTerm.app" ]; then  
    osascript \
      -e 'tell application "iTerm2" to tell current window to set newWindow to (create tab with default profile)'\
      -e "tell application \"iTerm2\" to tell current session of newWindow to write text \"${@}\""
  fi
  
}


### start running DB with docker
echo "\n...running DBs from docker container"
newtabi "cd ${PWD} && sh dev_start_docker_dbs.sh" &&


### Build front + watch hot reload
echo "\n... buiilding assets js with hot reload"
newtabi "cd ${PWD} && sh dev_start_watch.sh" &&


### Run server
echo "\n... running flask server"
newtabi "cd ${PWD} && sh dev_start_venv.sh && sh dev_start_serve.sh" 


### Open server in browser
open http://localhost:7000
