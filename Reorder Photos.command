#!/bin/bash
cd "$(dirname "$0")"
python3 reorder-server.py
echo
read -n 1 -s -r -p "Press any key to close."
