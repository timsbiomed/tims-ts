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

bin/stop-ts.sh

deactivate

# This will delete anything that is not already in the git index (no need to be committed as well)
# Add anything you do not want to be lost to the git index first.
git clean -xdff \
  -e ".venv" \
  -e ".idea" \
  -e ".m2" \
  -e "tmp" \
  -e "bin/env.sh" \
  -e "loaders/*.zip" \
  -e "hapi-cli" \
  -e "hapi-jpa-ext/hapi-run/application-local.yaml"

git checkout .

bin/loaders-reset.sh




