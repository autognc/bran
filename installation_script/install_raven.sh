export LC_ALL=C.UTF-8
export LANG=C.UTF-8
pip install --upgrade pip
cd ravenML
pip install -e .
pip install pip-tools
cd ../ravenML-plugins
pip install --upgrade setuptools
pip install --upgrade entrypoints --ignore-installed entrypoints
pip install --upgrade ptyprocess --ignore-installed ptyprocess
pip install --upgrade terminado --ignore-installed terminado
pip install --upgrade qtconsole --ignore-installed qtconsolet
pip install --upgrade wrapt --ignore-installed wrapt
./install_all.sh