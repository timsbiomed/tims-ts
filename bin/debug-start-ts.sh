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

if [[ -z ${SS_VENV:-} ]]; then
  bin/.setup-servers-init.sh
  . bin/env.sh
fi

. "${SS_VENV}/bin/activate"

setup-servers \
        py-debug \
        postgres-docker \
              --work-dir  postgres \
              --docker-tag 14-bullseye \
              --dbs-host localhost \
              --dbs-port 5432 \
              --action dbs-start \
        hapi-jpa-starter \
              --work-dir hapi-extensions \
              --dbs-work-dir postgres \
              --git-url "git@github.com:ShahimEssaid/hapi-fhir-jpaserver-starter-clone-1.git" \
              --git-ref "image/v6.2.2-extensions" \
              --mvn-local-repo .m2 \
              --spring-profiles "local,extensions,something-else" \
              --action hapi-start \
              --java-debug \





