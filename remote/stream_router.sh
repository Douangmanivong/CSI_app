#!/bin/bash

ROUTER_IP="192.168.50.1"
ROUTER_USER="TPTPTPTP"
ROUTER_PASS="TPTPTPTP"
PORT=5000

LAPTOP_IP="192.168.50.67"

sshpass -p "$ROUTER_PASS" ssh -o StrictHostKeyChecking=no $ROUTER_USER@$ROUTER_IP \
"source /jffs/setup_env && /jffs/tcpdump -i \"\$IF\" -U -s 0 -w - icmp" | nc $LAPTOP_IP $PORT
