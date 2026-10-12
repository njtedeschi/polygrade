#!/usr/bin/env bash
# Gradescope runs this once, when the autograder image is built.
# Install whatever the language needs here; Bash is already available.

apt-get install -y python3 python3-pip

pip3 install -r /autograder/source/requirements.txt
