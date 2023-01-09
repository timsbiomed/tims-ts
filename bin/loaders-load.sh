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
  bin/.setup-servers-init.sh
  . bin/env.sh
fi

. "${TTS_VENV}/bin/activate"

bin/hapi-cli-install.sh
export HAPI_CLI="${TTS_HOME}/hapi-cli/v${HAPI_VERSION}/hapi-fhir-cli"
FHIR_API_BASE="$(bin/hapi-jpa-ext-fhir-url.sh)"
export FHIR_API_BASE
#
#echo HAPI_CLI = "$HAPI_CLI"
#echo FHIR_API_BASE = "$FHIR_API_BASE"
#
#exit 0

for d in $(find "$(cd ${TTS_HOME}/loaders; pwd)" -mindepth 1 -maxdepth 1 -type d | sort); do
#for d in "${TTS_HOME}/loaders"/*; do
  if [[ -d $d ]]; then
    if [[ $d == *.off ]]; then
      echo skipping loader: "$d"
      continue
    fi

    if [ -f "${d}/build.sh" ]; then
      echo building: "$d"
      "${d}/build.sh"
    fi

    if [ -f "${d}/load.sh" ]; then
      echo loading: "$d"
      chmod u+x "${d}/load.sh"
      "${d}/load.sh"
    fi
  fi
done
