
### just keeping notes for later here....




# echo "Do you wish to install this program?"
# select yn in "Yes" "No"; do
#     case $yn in
#         Yes ) 
#           echo "yeeees"; 
#           break;;
#         No ) 
#           exit;;
#     esac
# done



# while true; do
#     read -p "Do you wish to install this program? [y/n]" yn
#     case $yn in
#         [Yy]* ) 
#           echo "yeeees";
#           break;;
#         [Nn]* ) 
#           exit;;
#         * ) 
#           echo "Please answer 'y' (yes) or 'n' (no).";;
#     esac
# done


yn_default="y"
read -p "Do you wish to install virtual env (y/n)? " yn
if [ "$yn" = "" ] ;then
  yn=yn_default
fi
if [ "$yn" != "${yn#[Yy]}" ] ;then
  echo "yeeees"
else 
  echo "noo"
fi
