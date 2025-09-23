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

if [[ -n "${COVERALLS_REPO_TOKEN:-}" ]]; then
    echo "Submitting coverage to Coveralls..."
    
    # Debug: Show environment variables
    echo "Environment info:"
    echo "  GITHUB_SHA: ${GITHUB_SHA:-'not set'}"
    echo "  GITHUB_REPOSITORY: ${GITHUB_REPOSITORY:-'not set'}"
    echo "  CI_COMMIT: ${CI_COMMIT:-'not set'}"
    echo "  CI_BRANCH: ${CI_BRANCH:-'not set'}"
    
    # Check if we have git context
    if git rev-parse --git-dir >/dev/null 2>&1; then
        echo "Git repository found, using git context"
        echo "Git info:"
        echo "  Current commit: $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
        echo "  Current branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
        echo "  Repository root: $(git rev-parse --show-toplevel 2>/dev/null || echo 'unknown')"
        
        export GIT_DISCOVERY_ACROSS_FILESYSTEM=1
        git config --global --add safe.directory /app
        
        # Try coveralls with git context
        coveralls --rcfile=./.coveragerc && {
            echo "✅ Successfully submitted to Coveralls with git context!"
        } || {
            echo "❌ Failed with git context, trying GitHub Actions mode..."
            # Fallback to GitHub Actions mode
            coveralls --service=github --rcfile=./.coveragerc || {
                echo "❌ Failed to submit to Coveralls"
                echo "Coverage files still generated successfully"
            }
        }
    elif [[ -n "${GITHUB_SHA:-}" && -n "${GITHUB_REPOSITORY:-}" ]]; then
        echo "Using GitHub Actions environment for Coveralls"
        echo "GitHub Actions mode with:"
        echo "  Repository: ${GITHUB_REPOSITORY}"
        echo "  Commit SHA: ${GITHUB_SHA}"
        
        # Submit using GitHub Actions environment variables
        coveralls --service=github --rcfile=./.coveragerc && {
            echo "✅ Successfully submitted to Coveralls with GitHub Actions!"
        } || {
            echo "❌ Failed to submit to Coveralls in GitHub Actions mode"
            echo "Coverage files still generated successfully"
        }
    else
        echo "⚠️  No git or GitHub Actions environment found"
        echo "Attempting basic submission (may fail)..."
        coveralls --rcfile=./.coveragerc || {
            echo "❌ Failed to submit to Coveralls - insufficient environment info"
            echo "Coverage files generated:"
            echo "- coverage.xml: XML format coverage report"
            echo "- .coverage: Python coverage database"
        }
    fi
else
    echo "COVERALLS_REPO_TOKEN not set, skipping Coveralls submission"
fi

echo "Generate Django DBML"
./manage.py dbml >> db.dbml
echo "Done"
