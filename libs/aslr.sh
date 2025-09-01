#!/bin/bash

ASLR="/proc/sys/kernel/randomize_va_space"

if [[ $(cat $ASLR) == 0 ]];
then
    echo "ASLR is turned off. Turning on now..."
    echo 2 | sudo tee $ASLR
    echo "done."
else
    echo "ASLR is turned on. Turning off now..."
    echo 0 | sudo tee $ASLR
    echo "done."
fi