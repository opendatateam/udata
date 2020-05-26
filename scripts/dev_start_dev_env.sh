#!/bin/bash



# source venv/bin/activate
UDATA_VENV="venv"

echo "TERM_PROGRAM : ${TERM_PROGRAM}"


newtabi(){

  if [ $TERM_PROGRAM = "iTerm.app" ]; then  
    osascript \
      -e 'tell application "iTerm2" to tell current window to set newWindow to (create tab with default profile)'\
      -e "tell application \"iTerm2\" to tell current session of newWindow to write text \"${@}\""
  fi
}




### start running DB with docker
echo "\n...running DBs from docker container"
newtabi "cd ${PWD} && source ${UDATA_VENV}/bin/activate && sh ./scripts/dev_start_docker_dbs.sh"
sleep 3

### Build front + watch hot reload
echo "\n... buiilding assets js with hot reload"
newtabi "cd ${PWD} && sh ./scripts/dev_start_watch.sh"
sleep 3

### Run server
echo "\n... running flask server"
newtabi "cd ${PWD} && source ${UDATA_VENV}/bin/activate && sh ./scripts/dev_start_serve.sh" 
sleep 3

### Wait and open server in browser
sleep 10
open http://localhost:7000
