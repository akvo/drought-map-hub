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
    echo "Attempting to submit coverage to coveralls..."

    # Check if we're in a git repository
    if git rev-parse --git-dir >/dev/null 2>&1; then
        echo "Git repository found, submitting to coveralls"
        export GIT_DISCOVERY_ACROSS_FILESYSTEM=1
        git config --global --add safe.directory /app
        coveralls
    else
        echo "Warning: Not in a git repository (running in Docker container)."
        echo "Skipping coveralls submission."
        echo "Coverage reports have been generated successfully and are available above."
        echo ""
        echo "To submit coverage manually, run coveralls from the host system"
        echo "where the git repository is available."
    fi
else
    echo "COVERALLS_REPO_TOKEN not set, skipping coveralls submission"
fi

echo "Generate Django DBML"
./manage.py dbml >> db.dbml
echo "Done"
