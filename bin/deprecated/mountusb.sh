#!/usr/bin/bash

mountpoint -q $USBMNT || sudo mount /dev/usbtop
