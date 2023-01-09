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
  cp bin/env.sh.example  bin/env.sh
fi
. bin/env.sh

if [[ -z ${TTS_VENV:-} || ! -d ${TTS_VENV} ]]; then
  bin/.setup-servers-init.sh
  . bin/env.sh
fi

. "${TTS_VENV}/bin/activate"


if [[ ! -f hapi-cli/hapi-cli-v${HAPI_VERSION}.zip ]]; then
  mkdir -p "hapi-cli"
  wget --quiet \
    --output-document "hapi-cli/hapi-cli-v${HAPI_VERSION}.zip" \
    "https://github.com/hapifhir/hapi-fhir/releases/download/v${HAPI_VERSION}/hapi-fhir-${HAPI_VERSION}-cli.zip"
fi

if [[ ! -f hapi-cli/v${HAPI_VERSION}/hapi-fhir-cli.jar ]]; then
  mkdir -p "hapi-cli/v${HAPI_VERSION}"
  unzip "hapi-cli/hapi-cli-v${HAPI_VERSION}.zip" -d "hapi-cli/v${HAPI_VERSION}"
fi
