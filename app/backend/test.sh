#!/usr/bin/env bash
#shellcheck disable=SC3040

set -euo pipefail

pip -q install --upgrade pip
pip -q install --cache-dir=.pip -r requirements.txt

./manage.py migrate

echo "Running tests"
COVERAGE_PROCESS_START=./.coveragerc \
    coverage run --parallel-mode --concurrency=multiprocessing --rcfile=./.coveragerc \
    ./manage.py test --shuffle --parallel 4

echo "Coverage"
coverage combine --rcfile=./.coveragerc
coverage report -m --rcfile=./.coveragerc

if [[ -n "${COVERALLS_REPO_TOKEN:-}" ]]; then
    export GIT_DISCOVERY_ACROSS_FILESYSTEM=1
    git config --global --add safe.directory /app
    coveralls
fi

echo "Generate Django DBML"
./manage.py dbml >> db.dbml
echo "Done"
