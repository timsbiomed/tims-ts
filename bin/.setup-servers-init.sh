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
TTS_HOME=$(realpath "${DIR}/..")
cd "$TTS_HOME"
if [[ ! -f bin/env.sh ]]; then
  cp bin/env.sh.example bin/env.sh
fi
. bin/env.sh

if [[ -z ${TTS_VENV:-} || ! -d ${TTS_VENV} ]]; then
  python3 -m venv "${TTS_VENV:-.venv}"
  if [[ -z ${TTS_VENV:-} ]]; then
    echo >>bin/env.sh
    echo "TTS_VENV=${TTS_VENV:-.venv}" >>bin/env.sh
    . bin/env.sh
  fi
fi

. "${TTS_VENV}/bin/activate"
pip -q install -U pip
pip -q -q uninstall -y setup-servers yq==
pip -q install setup-servers==0.1.13 yq &>/dev/null
