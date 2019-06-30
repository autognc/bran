raven_plugin="notset"
plugin_flag=d

while getopts "p:" opt; do
    case "$opt" in
        p)
            plugin_flag=p
            raven_plugin=$OPTARG
     esac
done

export LC_ALL=C.UTF-8
export LANG=C.UTF-8
pip install --upgrade pip
cd ravenML
pip install -e .
pip install pip-tools
cd ../ravenML-plugins
cd $raven_plugin
pip install --upgrade setuptools
pip install --upgrade entrypoints --ignore-installed entrypoints
pip install --upgrade ptyprocess --ignore-installed ptyprocess
pip install --upgrade terminado --ignore-installed terminado
pip install --upgrade qtconsole --ignore-installed qtconsole
pip install --upgrade wrapt --ignore-installed wrapt
./install.sh
ravenml config update --no-user -d skr-datasets-test1 -m skr-models-test1