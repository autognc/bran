raven_plugin="notset"
gpu_or_cpu="notset"
plugin_flag=d
gpu_flag=d

while getopts "pg:" opt; do
    case "$opt" in
        p)
            plugin_flag=p
            raven_plugin=$OPTARG
            ;;

        g)
            gpu_flag=g
            gpu_or_cpu=$OPTARG
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
if [ $gpu_or_cpu == 'gpu' ]
    then
        ./install.sh -g
    else
        ./install.sh
fi
ravenml config update --no-user -d skr-datasets-test1 -m skr-models-test1