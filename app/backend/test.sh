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
echo "- coverage.xml: XML format coverage report"
echo "- .coverage: Python coverage database"
# echo ""
# if [[ -n "${COVERALLS_REPO_TOKEN:-}" ]]; then
#     if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
#         echo "Running in GitHub Actions - Coveralls submission will be handled by GitHub Actions step"
#     else
#         echo "Running locally with COVERALLS_REPO_TOKEN - attempting direct submission"
#         echo "Attempting to submit coverage to Coveralls..."
#         export GIT_DISCOVERY_ACROSS_FILESYSTEM=1
#         git config --global --add safe.directory /app

#         # Try coveralls submission with error handling
#         if coveralls; then
#             echo "✅ Successfully submitted coverage to Coveralls!"
#         else
#             coveralls_exit_code=$?
#             echo "❌ Failed to submit coverage to Coveralls (exit code: $coveralls_exit_code)"
#             echo "This could be due to:"
#             echo "  - Coveralls server issues (500 errors)"
#             echo "  - Network connectivity problems"
#             echo "  - API rate limiting"
#             echo ""
#             echo "Build will continue despite Coveralls submission failure."
#         fi
#     fi
# else
#     echo "COVERALLS_REPO_TOKEN not set, skipping Coveralls submission"
# fi

echo "Generate Django DBML"
./manage.py dbml >> db.dbml
echo "Done"
