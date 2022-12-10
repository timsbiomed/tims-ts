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

setup-servers \
        postgres-docker \
              --work-dir  postgres \
              --docker-tag 14-bullseye \
              --dbs-host localhost \
              --dbs-port 5432 \
              --action dbs-start \
        hapi-jpa-starter \
              --work-dir hapi-jpa-ext \
              --dbs-work-dir postgres \
              --git-url "git@github.com:ShahimEssaid/hapi-fhir-jpaserver-starter-clone-1.git" \
              --git-ref "image/v6.2.2-extensions" \
              --mvn-local-repo ../.m2 \
              --spring-profiles "local,ext" \
              --action hapi-start \





