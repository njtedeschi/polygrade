#!/usr/bin/env bash
# Gradescope runs this once, when the autograder image is built.

apt-get install -y python3 python3-pip

pip3 install -r /autograder/source/requirements.txt

# Install Java
apt-get install -y default-jdk

# Dynamically find the Java installation path and add it to PATH
JAVA_PATH=$(update-alternatives --list java | sed 's|/bin/java||')
echo "export PATH=\$PATH:$JAVA_PATH" >> ~/.profile
source ~/.profile

# Install Leiningen (the Clojure build tool)
wget https://raw.githubusercontent.com/technomancy/leiningen/stable/bin/lein
mv lein /usr/local/bin
chmod a+x /usr/local/bin/lein
lein

# Install the lein-exec plugin globally, for running standalone scripts
mkdir -p ~/.lein
echo "{:user {:plugins [[lein-exec \"0.3.7\"]]}}" > ~/.lein/profiles.clj

# Download the plugin and its dependencies now rather than while grading
lein
