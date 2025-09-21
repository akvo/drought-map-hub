#!/usr/bin/env bash
set -euo pipefail

# configure-test.sh
# Consolidated tests ported from .github/workflows/test.yml
# This script is intended to be run locally to exercise the same checks
# the CI workflow performs. Use with care: it may create/modify .env files.

usage() {
	cat <<'USAGE'
Usage: ./configure-test.sh [--dry-run]

Options:
	--dry-run    Only perform syntax checks and dry-run actions where available
	-h, --help   Show this help
USAGE
}

DRY_RUN=false
while [[ ${#} -gt 0 ]]; do
	case "$1" in
		--dry-run) DRY_RUN=true; shift ;;
		-h|--help) usage; exit 0 ;;
		*) echo "Unknown argument: $1"; usage; exit 2 ;;
	esac
done

echo "Starting consolidated configure tests (dry-run=${DRY_RUN})"

# Ensure required tools are available (attempt to install if run with sudo)
ensure_tools() {
	local missing=()
	for cmd in bc expect; do
		if ! command -v "$cmd" >/dev/null 2>&1; then
			missing+=("$cmd")
		fi
	done
	if [[ ${#missing[@]} -gt 0 ]]; then
		echo "Missing tools: ${missing[*]}. Attempting to install via apt-get (requires sudo)."
		if command -v apt-get >/dev/null 2>&1 && [[ $EUID -eq 0 ]]; then
			apt-get update && apt-get install -y "${missing[@]}"
		else
			echo "Please install: ${missing[*]} and re-run this script." >&2
			return 1
		fi
	fi
	return 0
}

if ! ensure_tools; then
	echo "Tool check failed - continuing may fail." >&2
fi

echo "Making scripts executable..."
chmod +x configure.sh || true
chmod +x run.sh || true

# 1) Test run.sh dry-run mode for combinations similar to matrix
modes=(dev prod)
services=(all app cdi geonode)

for mode in "${modes[@]}"; do
	for service in "${services[@]}"; do
		echo "Testing run.sh with mode=${mode} service=${service}"
		if $DRY_RUN; then
			./run.sh mode=${mode} service=${service} --dry-run || {
				echo "run.sh dry-run failed for mode=${mode} service=${service}" >&2
			}
		else
			# still run but capture non-zero exit to continue
			./run.sh mode=${mode} service=${service} --dry-run || true
		fi
	done
done

# 2) Test run.sh help
echo "Testing run.sh help output"
./run.sh --help || true
./run.sh -h || true

# 3) Automate configure.sh interactive inputs using expect
echo "Running automated configure.sh interaction via expect"
cat > test_install.exp <<'EOF'
#!/usr/bin/expect -f
set timeout 60

spawn ./configure.sh

# Email configuration
expect { -re "EMAIL_HOST.*" { send "smtp.test.com\r" } }
expect { -re "EMAIL_PORT.*" { send "2525\r" } }
expect { -re "EMAIL_USE_TLS.*" { send "True\r" } }
expect { -re "EMAIL_HOST_USER.*" { send "testuser@test.com\r" } }
expect { -re "EMAIL_HOST_PASSWORD.*" { send "testpass\r" } }
expect { -re "EMAIL_FROM.*" { send "noreply@test.com\r" } }

# Earth data username
expect { -re "Username.*" { send "testuser\r" } }

# Earth data password
expect { -re "Password.*" { send "testpass\r" } }

# Drought hub domain
expect { -re "Drought-map Hub Domain.*" { send "http://test.example.com\r" } }

# Geonode domain
expect { -re "Geonode Domain.*" { send "http://geonode.test.com\r" } }

# Service selection (choose option 2 as in CI)
expect { -re "Which services would you like to run.*" { send "2\r" } }

# Geonode config for app service
expect { -re "Geonode Base URL.*" { send "http://geonode.app.com\r" } }
expect { -re "Geonode Admin Username.*" { send "adminuser\r" } }
expect { -re "Geonode Admin Password.*" { send "adminpass\r" } }

# Mode selection (1 = development)
expect { -re "Would you like to run in development or production mode.*" { send "1\r" } }

expect eof
EOF

chmod +x test_install.exp

# Run expect script; allow failure but capture exit code
if $DRY_RUN; then
	echo "Skipping actual configure.sh interaction in dry-run mode"
else
	./test_install.exp || echo "configure.sh automated interaction exited non-zero"
fi

# 4) Verify generated files
echo "Verifying generated configuration files"
failures=0
check_file() {
	local path="$1"; shift
	if [[ ! -f "$path" ]]; then
		echo "$path not created" >&2
		failures=$((failures+1))
		return 1
	fi
	return 0
}

check_file app/.env || true
check_file cdi/.env || true
check_file geonode/.env || true
check_file traefik/.env || true
check_file cdi/config/cdi_project_settings.json || true

if [[ -f app/.env ]]; then
	grep -q "smtp.test.com" app/.env || { echo "Email host not found in app/.env" >&2; failures=$((failures+1)); }
fi
if [[ -f cdi/.env ]]; then
	grep -q "testuser" cdi/.env || { echo "Earth data username not found in cdi/.env" >&2; failures=$((failures+1)); }
fi
if [[ -f traefik/.env ]]; then
	grep -q "http://test.example.com" traefik/.env || { echo "Domain not found in traefik/.env" >&2; failures=$((failures+1)); }
fi
if [[ -f app/.env ]]; then
	grep -q "adminuser" app/.env || { echo "Geonode admin username not found in app/.env" >&2; failures=$((failures+1)); }
fi

if [[ $failures -eq 0 ]]; then
	echo "All configuration files generated (or checks skipped)"
else
	echo "$failures verification failures detected" >&2
fi

# Optionally display generated files for debugging
echo "Displaying generated configs (if present)"
[[ -f app/.env ]] && { echo "=== app/.env ==="; sed -n '1,200p' app/.env; }
echo
[[ -f cdi/.env ]] && { echo "=== cdi/.env ==="; sed -n '1,200p' cdi/.env; }
echo
[[ -f traefik/.env ]] && { echo "=== traefik/.env ==="; sed -n '1,200p' traefik/.env; }
echo
[[ -f cdi/config/cdi_project_settings.json ]] && { echo "=== cdi/config/cdi_project_settings.json ==="; sed -n '1,200p' cdi/config/cdi_project_settings.json; }

# 5) Error-handling tests for run.sh
echo "Running run.sh error-handling tests"

run_expect_fail() {
	local cmd=("$@")
	if "${cmd[@]}"; then
		echo "Expected failure but command succeeded: ${cmd[*]}" >&2
		return 1
	else
		echo "Correctly rejected invalid invocation: ${cmd[*]}"
		return 0
	fi
}

# Invalid mode
run_expect_fail ./run.sh mode=invalid service=all --dry-run || true

# Invalid service
run_expect_fail ./run.sh mode=dev service=invalid --dry-run || true

# Missing arguments
run_expect_fail ./run.sh mode=dev --dry-run || true
run_expect_fail ./run.sh service=all --dry-run || true

# Valid invocations
echo "Running accepted run.sh invocations (dry-run)"
./run.sh mode=dev service=all --dry-run || true
./run.sh mode=prod service=app --dry-run || true
./run.sh mode=dev service=cdi --dry-run || true
./run.sh mode=prod service=geonode --dry-run || true

echo "configure-test.sh completed"
