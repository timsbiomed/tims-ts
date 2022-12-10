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

if [[ -z ${TT_VENV:-} || ! -d ${TT_VENV} ]]; then
  bin/.setup-servers-init.sh
  . bin/env.sh
fi

. "${TT_VENV}/bin/activate"

bin/stop-ts.sh

# This will delete anything that is not already in the git index (no need to be committed as well)
# Add anything you do not want to be lost to the git index first.
git clean -xdff -e ".idea" -e ".m2" -e "bin/env.sh"
git checkout .




