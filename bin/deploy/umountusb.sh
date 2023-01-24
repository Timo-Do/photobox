#!/usr/bin/bash

mountpoint -q $USBMNT && sudo systemd-umount /dev/usbtop
