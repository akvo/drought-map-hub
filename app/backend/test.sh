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
coverage xml --rcfile=./.coveragerc

if [[ -n "${COVERALLS_REPO_TOKEN:-}" ]]; then
    echo "Submitting coverage to Coveralls..."

    # Check if we have git context, if not, use GitHub Actions environment
    if git rev-parse --git-dir >/dev/null 2>&1; then
        echo "Git repository found, using git context"
        export GIT_DISCOVERY_ACROSS_FILESYSTEM=1
        git config --global --add safe.directory /app
        coveralls --rcfile=./.coveragerc
    elif [[ -n "${GITHUB_SHA:-}" && -n "${GITHUB_REPOSITORY:-}" ]]; then
        echo "Using GitHub Actions environment for Coveralls"
        # Submit using GitHub Actions environment variables
        coveralls --service=github --rcfile=./.coveragerc
    else
        echo "No git or GitHub Actions environment found, attempting basic submission"
        coveralls --rcfile=./.coveragerc || {
            echo "Failed to submit to Coveralls - no git context available"
            echo "Coverage files generated:"
            echo "- coverage.xml: XML format coverage report"
            echo "- .coverage: Python coverage database"
        }
    fi
fi

echo "Generate Django DBML"
./manage.py dbml >> db.dbml
echo "Done"
