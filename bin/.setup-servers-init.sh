#!/usr/bin/env bash

#set -x
set -e
set -u
set -o pipefail
set -o noclobber
shopt -s nullglob

# stack overflow #59895
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
TT_HOME=$(realpath "${DIR}/..")
cd "$TT_HOME"
if [[ ! -f bin/env.sh ]]; then
  cp bin/env.sh.example  bin/env.sh
fi
. bin/env.sh

if [[ -z $TT_VENV || ! -d ${TT_VENV}  ]]; then
  python3  -m venv "${TT_VENV:-.venv}"
  echo >> bin/env.sh
  echo "TT_VENV=${TT_VENV:-.venv}" >> bin/env.sh
  . bin/env.sh
fi

. "${TT_VENV}/bin/activate"
pip -q install -U pip
pip -q -q uninstall -y setup-servers yq
pip -q install setup-servers==0.1.12 yq &> /dev/null

