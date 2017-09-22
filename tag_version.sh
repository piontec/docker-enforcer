#!/bin/bash -e

VER=$(egrep "^version = \"[0-9]+" dockerenforcer/config.py |cut -f2 -d"=" | tr -d " \"")
git tag -a -m "release ${VER}" ${VER}
echo "Tagged with ${VER}"
