#!/bin/bash


### - - - - - - - - - - - - - - - ### 

### NEED PYTHON 3.* INSTALLED
### NEED DOCKER INSTALLED

### WORKING ON MAC OS / CATARINA

### SPOKEN PARTS WRITTEN IN FRENCH ....

### - - - - - - - - - - - - - - - ### 



echo
echo ">>> INSTALLING UDATA WITH DATAGOUV  THEME ... "

echo 
## cf https://stackoverflow.com/questions/3466166/how-to-check-if-running-in-cygwin-mac-or-linux/18790824
if [ "$(uname)" == "Darwin" ]; then
  # Do something under Mac OS X platform 
  OS_CHOSEN="MAC OS"
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
  # Do something under GNU/Linux platform
  OS_CHOSEN="LINUX"
elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW32_NT" ]; then
  # Do something under 32 bits Windows NT platform
  OS_CHOSEN="WINDOWS 32"
elif [ "$(expr substr $(uname -s) 1 10)" == "MINGW64_NT" ]; then
  # Do something under 64 bits Windows NT platform
  OS_CHOSEN="WINDOWS 64"
else 
  echo "OTHER"
  OS_CHOSEN="OTHER"
fi

echo "OS_CHOSEN : ${OS_CHOSEN}"



### - - - - - - - - - - - - - - - ### 
### MAIN FUNCTIONS
### - - - - - - - - - - - - - - - ### 

newtabi(){

  ### 
  if [ $TERM_PROGRAM = "iTerm.app" ]; then  
    osascript \
      -e 'tell application "iTerm2" to tell current window to set newWindow to (create tab with default profile)'\
      -e "tell application \"iTerm2\" to tell current session of newWindow to write text \"${@}\""
  else 
    echo "... error newtabi / no TERM_PROGRAM..."
  fi
  
}

# function for saying stuff
say_what(){
  if [[ "${OS_CHOSEN}" = "WINDOWS 64" || "${OS_CHOSEN}" = "LINUX" ]]; then
    echo -en "\007"
    echo "$S1" 
    # | espeak
    # PowerShell -Command "Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('${S1}');"
  elif [ "${OS_CHOSEN}" = "MAC OS" ] ; then
    say "$1"
  else 
    echo "$1"
  fi
}

# #say_what "votre OS est ${OS_CHOSEN}"


### - - - - - - - - - - - - - - - ### 
### MAIN VARIABLES
### - - - - - - - - - - - - - - - ### 

JOB_TITLE="Installation uData & datagouv.fr thème"
SCRIPT_VERSION="v.1.4"
LAST_UPDATE="05/04/2020"

UDATA_REPO="https://github.com/opendatateam/udata.git"
UDATA_FOLDER=$(basename $PWD)
UDATA_VENV="venv"

UDATA_GOUVFR_REPO="https://github.com/etalab/udata-gouvfr.git"
UDATA_GOUVFR_FOLDER="udata-gouvfr"

STEPPER="\n............................................\n" 
SPACER="\n\n\n\n"
CANCEL="CANCELLED"
CONTINUER="Voulez-vous continuer ? "



### - - - - - - - - - - - - - - - ### 


echo "${SPACER}"
echo "${STEPPER} "
echo "         HELLO ! "
echo "${STEPPER} "
echo " - SCRIPT VERSION : ${SCRIPT_VERSION}"
echo " - LAST UPDATE : ${LAST_UPDATE}"
echo " - PWD : ${PWD}"
echo " - UDATA_FOLDER : ${UDATA_FOLDER}"
echo "${STEPPER} "
echo "        !!! NOW STARTING SCRIPTS !!! "
echo "${STEPPER} "


# say "Bienvenue ! Ceci est le script $JOB_TITLE "
sleep .5
echo


# #say_what "${CONTINUER}"
read -p "Do you wish to continue (y/n)? " yn
echo

if [ "$yn" != "${yn#[Yy]}" ] ;then


  ### - - - - - - - - - - - - - - - ### 
  ### VIRTUAL ENV
  ### - - - - - - - - - - - - - - - ### 
  echo "${STEPPER}"
  yn_default="y"
  read -p "Do you wish to install virtual env (y/n)? " yn
  echo
  if [ "$yn" = "" ] ;then
    yn=yn_default
  fi
  if [ "$yn" != "${yn#[Yy]}" ] ;then

    echo "${STEPPER} "
    STEP_N="Setting up : PYTHON_VIRTUAL_ENV" 
    echo $STEP_N
    echo
    sleep .2

    
    # instal virtual env
    read -p "- ${STEP_N} - please enter the name of your udata virtual environment [venv]? " udata_venv
    if [ "$udata_venv" != "" ] ;then
      UDATA_VENV=$udata_venv
      echo 
    else
      echo
    fi

    echo "UDATA_VENV : ${UDATA_VENV}"

    pip install virtualenv
    virtualenv $UDATA_VENV 
    source $UDATA_VENV/bin/activate 

    # install requirements in venv
    pip install -r requirements/develop.pip
    pip install -e .


    #say_what "$STEP_N - étape terminée"
  else
    echo 
  fi




  ### - - - - - - - - - - - - - - - ### 
  ### DOCKER CONTAINERS 
  ### - - - - - - - - - - - - - - - ### 
  echo "${STEPPER}"
  STEP_N="Running DBs : MONNGODB_ELASTICSEARCH" 
  echo $STEP_N
  echo
  sleep .2

  #docker-compose up
  newtabi "cd ${PWD} && sh ./scripts/dev_start_docker_dbs.sh"


  #say_what "$STEP_N - étape terminée"





  ### - - - - - - - - - - - - - - - ### 
  ### NODE JS
  ### - - - - - - - - - - - - - - - ### 
  echo "${STEPPER}"
  yn_default="y"
  read -p "Do you wish to rebuild NVM (y/n)? " yn
  echo
  if [ "$yn" = "" ] ;then
    yn=yn_default
  fi
  if [ "$yn" != "${yn#[Yy]}" ] ;then
    echo "${STEPPER}"
    STEP_N="Setting up : NODE_JS" 
    echo $STEP_N
    echo
    sleep .2

    # install nvm
    brew install nvm
    export NVM_DIR="$HOME/.nvm"
      [ -s "/usr/local/opt/nvm/nvm.sh" ] && . "/usr/local/opt/nvm/nvm.sh"  # This loads nvm
      [ -s "/usr/local/opt/nvm/etc/bash_completion.d/nvm" ] && . "/usr/local/opt/nvm/etc/bash_completion.d/nvm" # This loads nvm bash_completion

    nvm install 
    nvm use

    # install JS dependencies
    npm install

    # build assets and widgets
    inv assets-build
    inv widgets-build
  else
    echo 
  fi




  ### - - - - - - - - - - - - - - - ### 
  ### THEME : UDATA-GOUVFR
  ### - - - - - - - - - - - - - - - ### 
  echo "${STEPPER}"
  STEP_N="Importing theme : THEME_UDATAGOUVFR" 
  echo $STEP_N
  echo
  sleep .2


  # instal theme 
  yn_default="n"
  read -p "- ${STEP_N} - Do you want to install DATAGOUV-FR theme (y/n)? " answer
  if [ "$yn" = "" ] ;then
    yn=yn_default
  fi
  if [ "$answer" != "${answer#[Yy]}" ] ;then

    #rm udata.cfg
    echo >> udata.cfg
    echo "PLUGINS = ['gouvfr']" >> udata.cfg
    echo "THEME = 'gouvfr'" >> udata.cfg

    read -p "- ${STEP_N} - Do you want to install datagouvfr theme for local development (y/n)? " answer

    if [ "$answer" != "${answer#[Yy]}" ] ;then

      read -p "- ${STEP_N} - Precise the name you'd like for the theme's folder [${UDATA_GOUVFR_FOLDER}]? " new_folder
      if [ "$new_folder" != "" ] ;then
        UDATA_GOUVFR_FOLDER=$new_folder
        echo 
      else
        echo
      fi

      echo "UDATA_GOUVFR_FOLDER : ${UDATA_GOUVFR_FOLDER}"
      sleep .5

      ### clone theme repo from upper
      cd ..
      git clone $UDATA_GOUVFR_REPO $UDATA_GOUVFR_FOLDER

      # source $UDATA_VENV/bin/activate 
      pip install -e $UDATA_GOUVFR_FOLDER

      cd $UDATA_GOUVFR_FOLDER 
      npm install
      inv assets-build
      echo 

    else
      ### install udata-gouvfr module
      echo
      pip install udata-gouvfr
    fi

    ### back to udata folder 
    cd ..
    cd $UDATA_FOLDER
    echo "PWD after theme : ${PWD}"

  else
    ### don't install any theme
    echo
  fi


  #say_what "$STEP_N - étape terminée"





  ### - - - - - - - - - - - - - - - ### 
  ### UDATA INITIALIZATION
  ### - - - - - - - - - - - - - - - ### 
  echo "${STEPPER}"
  echo 
  STEP_N="Initializing uData DB : ..." 
  echo $STEP_N
  echo
  sleep .2


  # Initialize database, indexes...
  source $UDATA_VENV/bin/activate 
  udata init

  # Optionnaly fetch and load some licenses from another udata instance
  udata licenses https://www.data.gouv.fr/api/1/datasets/licenses

  # Compile translations
  inv i18nc




  ### - - - - - - - - - - - - - - - ### 
  ### RUNNING UDATA
  ### - - - - - - - - - - - - - - - ### 
  echo "${STEPPER}"
  echo 
  STEP_N="Initializing uData : ..." 
  echo $STEP_N
  echo
  sleep .2


  # Build front + watch hot reload
  newtabi "cd ${PWD} && source ${UDATA_VENV}/bin/activate && sh ./scripts/dev_start_watch.sh"

  # Run server
  #say_what "$STEP_N - étape terminée"
  newtabi "cd ${PWD} && source ${UDATA_VENV}/bin/activate && sh ./scripts/dev_start_serve.sh" 


  ### - - - - - - - - - - - - - - - ### 
  # open http://localhost:7000


fi



sleep 2
echo 
echo ............................................
echo
echo "   CONGRATS ! "
echo "     The job ..."
echo "       '${JOB_TITLE}' "
echo "         ... is now completed !"
echo
echo ............................................

#say_what "Le script est maintenant terminé ..."
sleep .5


exit