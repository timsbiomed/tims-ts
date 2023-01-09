#!/usr/bin/env bash
#
# download and place a SNOMED-CD release file in this folder, and name it SNOMEDCT.zip

set -x
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

cd "$DIR"

if [ -f "loading.txt" ] || [ -f "loaded.txt" ]; then
  echo Skipping: "${DIR}/SNOMEDCT.zip"
  exit 0
fi

if [[ -f SNOMEDCT.zip ]]; then
  if ${HAPI_CLI} \
    upload-terminology \
    -d "SNOMEDCT.zip" \
    -v r4 \
    -t "${FHIR_API_BASE}" \
    -u http://snomed.info/sct > "loading.txt" 2>&1; then
    mv "loading.txt" "loaded.txt"
  fi
fi
