#!/usr/bin/env bash
# Gradescope runs this once, when the autograder image is built.

apt-get install -y python3 python3-pip

pip3 install -r /autograder/source/requirements.txt
