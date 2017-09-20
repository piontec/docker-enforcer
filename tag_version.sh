#!/bin/bash -e

VER=$(grep "version = " dockerenforcer/config.py |cut -f2 -d"=" | tr -d " \"")
git tag -a -m "release ${VER}" ${VER}
echo "Tagged with ${VER}"
