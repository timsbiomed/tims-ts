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
SS_HOME=$(realpath "${DIR}/..")
cd "$SS_HOME"
. bin/env.sh

if [[ -z $SS_VENV ]]; then
  python3  -m venv .venv
  echo >> bin/env.sh
  echo "SS_VENV=.venv" >> bin/env.sh
  . bin/env.sh
fi

. "${SS_VENV}/bin/activate"
pip -q install -U pip
pip -q -q uninstall -y setup-servers
pip -q install setup-servers==0.1.10

