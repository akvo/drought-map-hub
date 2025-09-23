#!/usr/bin/env bash
#shellcheck disable=SC3040

set -euo pipefail

# Install git if not available (needed for coveralls)
if ! command -v git >/dev/null 2>&1; then
    echo "Installing git for coveralls..."
    apt-get update -qq && apt-get install -y -qq git
fi

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
coverage xml --rcfile=./.coveragerc

echo "Coverage files generated:"
echo "- coverage.xml: XML format coverage report (for Coveralls)"
echo "- .coverage: Python coverage database"
echo ""
echo "Coveralls submission will be handled by GitHub Actions if COVERALLS_REPO_TOKEN is set"

echo "Generate Django DBML"
./manage.py dbml >> db.dbml
echo "Done"
