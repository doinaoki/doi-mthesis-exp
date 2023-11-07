#!/usr/bin/env bash
while getopts "f" opt; do
    case $opt in
        "f" ) 
            echo "set force mode"
            FORCE="TRUE"
            ;;
    esac
done
shift $(expr $OPTIND - 1) # remove option args
JARPATH="AbbrExpansion/out"
PARSECODE="ParseCode.jar"
SEMANTICEXPAND="SemanticExpand.jar"
IDTABLE="idTable.csv"
EXTABLE="exTable.csv"
GZIP_IDTABLE=${IDTABLE}".gz"
GZIP_EXTABLE=${EXTABLE}".gz"
IDTABLE_PATH="${archive}/${IDTABLE}"
EXTABLE_PATH="${archive}/${EXTABLE}"
GZIP_IDTABLE_PATH="${archive}/${GZIP_IDTABLE}"
GZIP_EXTABLE_PATH="${archive}/${GZIP_EXTABLE}"
VERSION=$(bash --version | head -n 1 | sed -E 's/^.* ([0-9.]+)\.[0-9]+\([0-9]+\)-release.*$/\1/')

# bash requirement check
# if [[ $(echo "${VERSION} < 4.3" | bc) -eq 1 ]] ; then
#     echo "bash version must be 4.3 or later"
#     exit
# fi

# renas
set -e
archive=${1%/}
echo "${archive}"
echo "start creating table."

# remove jar signature
if [ -n "$(zipinfo -1 ${JARPATH}/${PARSECODE} | grep META-INF/.*SF)" ]; then
    echo "rm META-INF/*SF"
    zip -d "${JARPATH}/${PARSECODE}" 'META-INF/*SF'
fi
# create table
if [ "$FORCE" = "TRUE" ] || [ ! -f "${GZIP_EXTABLE_PATH}" ]; then
    echo "${archive} Run ParseCode"
    repo=${archive}"/repo"
    # parse code
    java -jar "${JARPATH}/${PARSECODE}" "${archive}"
    # semantic expand
    java -jar "${JARPATH}/${SEMANTICEXPAND}" "${archive}"
    # normalize
    python -m renas.normalize "${archive}"
    # gzip
    echo "gzip tables"
    gzip -f "${archive}/${IDTABLE}"
    gzip -f "${archive}/${EXTABLE}"
else
    echo "${IDTABLE_PATH} already exists. Skip."
fi
