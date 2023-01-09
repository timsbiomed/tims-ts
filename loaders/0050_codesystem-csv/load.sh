#!/usr/bin/env bash
#set -x
set -e
set -u
set -o pipefail
set -o noclobber
#set -f # no globbing
#shopt -s failglob # fail if glob doesn't expand

# See http://stackoverflow.com/questions/getting-the-source-directory-of-a-bash-script-from-within
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
cd ${DIR}

for f in $(find "$(
  cd "${DIR}"
  pwd
)" -mindepth 1 -maxdepth 1 -type f -name "*.zip" | sort); do

  if [ -f "${f}.loaded.txt" ] || [ -f "${f}.loading.txt" ]; then
    echo "Already loaded/loading: ${DIR}/${f}, SKIPPING IT"
    continue
  fi

  echo loading: "${DIR}/${f}"

  if ${HAPI_CLI} \
    upload-terminology \
    -d "${f}" \
    -v r4 \
    -t "${FHIR_API_BASE}" \
    -u http://snomed.info/sct >"${f}.loading.txt" 2>&1; then
    mv "${f}.loading.txt" "${f}.loaded.txt"
  fi
done
