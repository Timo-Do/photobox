#!/usr/bin/bash



# Send files to pi
rsync -av --delete deploy pi@$RASPI:photobox/

ssh -t -t "pi@$RASPI" "\
    export DISPLAY=:0;
    \source ~/pb-dev/bin/activate;\
    cd ~/photobox/deploy;\
    python ~/photobox/deploy/$1"
