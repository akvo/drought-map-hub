import os
import json
import time
import contextlib
import requests

geonode_url = os.getenv("GEONODE_URL")
username = os.getenv("GEONODE_USERNAME")
password = os.getenv("GEONODE_PASSWORD")
dataset_path = "../../output_data/GeoTiffs"
dataset_type = ".tif"

VERIFY = True

# Polling settings for tracking_upload_progress. The previous implementation
# recursed without sleeping, which hammered GeoNode and blew the Python
# recursion limit ("maximum recursion depth exceeded") on slow imports.
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 600

# (connect, read) timeouts for every HTTP call. requests blocks FOREVER by
# default, so a server that accepts the connection and then stops answering -
# or one that drops packets outright - hangs the job indefinitely. That also
# defeats POLL_TIMEOUT_SECONDS, which is only checked between requests, and
# the circuit breaker below, which needs an exception to count a failure.
# Without these the job goes quiet during an outage instead of aborting.
REQUEST_TIMEOUT = (10, 60)
# The upload POST streams a raster and waits for GeoNode to accept it, so it
# needs a longer read budget than a status poll.
UPLOAD_TIMEOUT = (10, 300)

# Files that failed to upload are recorded here so the next run retries them
# before anything else. Every run re-uploads all rasters anyway (percent ranks
# shift whenever a new month arrives), so this only controls ordering and
# gives operators a record of what broke.
FAILURE_LOG_PATH = "../../logs/upload_failures.json"

# Abort the run after this many uploads fail back-to-back. A GeoServer outage
# fails every remaining file identically, so there is no point churning
# through hundreds of them.
MAX_CONSECUTIVE_FAILURES = 5


class UploadCircuitBreaker(Exception):
    """Raised when too many uploads fail consecutively."""


def get_categories(api_url, file_name="geonode_category.json"):
    try:
        # Fetch data from the API
        response = requests.get(
            api_url, verify=VERIFY, timeout=REQUEST_TIMEOUT
        )
        # Will raise an error for 4xx or 5xx status codes
        response.raise_for_status()

        selected_categories = [
            "cdi-raster-map",
            "spi-raster-map",
            "evi2-raster-map",  # was ndvi-raster-map
            "esi-raster-map",   # was lst-raster-map
            "sm-raster-map"     # SM now has weight > 0 and is exported
        ]
        categories = response.json().get("objects")
        categories = list(filter(
            lambda x: x["identifier"] in selected_categories,
            categories
        ))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return {}

    # Convert list to dictionary
    category = {c['identifier'].split('-')[0]: c['id'] for c in categories}

    # Check if the file exists
    if not os.path.exists(file_name):
        # Write dictionary to JSON file
        with open(file_name, 'w') as json_file:
            json.dump(category, json_file, indent=4)

    # Read and return the contents of the JSON file
    with open(file_name, 'r') as json_file:
        return json.load(json_file)


def write_failure_message(response):
    print("Request failed.")
    print("Status Code:", response.status_code)
    print("Response:", response.text)


def upload_to_geonode(base_file_path, xml_file_path=None, sld_file_path=None):
    api_url = f"{geonode_url}/api/v2/uploads/upload?format=json"
    paths = {"base_file": base_file_path}
    if xml_file_path:
        paths["xml_file"] = xml_file_path
    if sld_file_path:
        paths["sld_file"] = sld_file_path
    data = {
        "store_spatial_files": False,
        "overwrite_existing_layer": True,
        "skip_existing_layers": False,
    }
    with contextlib.ExitStack() as stack:
        files = {
            key: stack.enter_context(open(path, "rb"))
            for key, path in paths.items()
        }
        response = requests.post(
            api_url,
            auth=(username, password),
            files=files,
            data=data,
            verify=VERIFY,
            timeout=UPLOAD_TIMEOUT,
        )
    if response.status_code == 201:
        json_response = response.json()
        return json_response.get("execution_id")
    else:
        write_failure_message(response)
        return None


def get_all_dataset_files():
    dataset_files = []
    for root, dirs, files in os.walk(dataset_path):
        for file in files:
            if file.endswith(dataset_type):
                dataset_files.append(os.path.join(root, file))
    return dataset_files


def get_recent_files(limit=None):
    dataset_files = []

    for root, dirs, files in os.walk(dataset_path):
        for file in files:
            if file.endswith(dataset_type):
                file_path = os.path.join(root, file)
                dataset_files.append((file_path, os.path.getmtime(file_path)))

    # Sort files by category (alphabetically) then by modification time (newest first)
    # Categories: CDI, ESI, EVI2, SM, SPI
    def sort_key(item):
        path, mtime = item
        category = path.split('/')[-2]  # Get category from path
        return (category, -mtime)  # Sort by category name, then negative mtime for newest first
    dataset_files.sort(key=sort_key)

    # Extract file paths, limited to `limit` if provided
    if limit:
        recent_files = [file[0] for file in dataset_files[:limit]]
    else:
        recent_files = [file[0] for file in dataset_files]

    # Raise an error if no files are found
    if not recent_files:
        raise FileNotFoundError(
            f"No files with extension '{dataset_type}' found in {dataset_path}"
        )

    return recent_files


def update_dataset_metadata(dataset_id, metadata):
    api_url = f"{geonode_url}/api/v2/datasets/{dataset_id}"
    response = requests.patch(
        api_url,
        auth=(username, password),
        json=metadata,
        verify=VERIFY,
        timeout=REQUEST_TIMEOUT
    )
    if response.status_code == 200:
        print("Dataset successfully uploaded!")
    else:
        write_failure_message(response)


def tracking_upload_progress(
    execution_id: int,
    taxonomy: str = None,
    categories: object = None,
    date_created: str = None,
    timeout: int = POLL_TIMEOUT_SECONDS,
    interval: int = POLL_INTERVAL_SECONDS,
):
    """Poll until the import finishes, then update the dataset metadata.

    Args:
        execution_id: GeoNode execution request id returned by the upload.
        taxonomy: Dataset category key (cdi/esi/evi2/spi/sm).
        categories: Mapping of taxonomy key to GeoNode category id.
        date_created: Metadata date, formatted YYYY-MM-01.
        timeout: Maximum seconds to wait for the import to finish.
        interval: Seconds to sleep between polls.

    Raises:
        RuntimeError: When GeoNode reports the import as failed.
        TimeoutError: When the import does not finish within `timeout`.
    """
    if not execution_id:
        return
    api_url = f"{geonode_url}/api/v2/executionrequest/{execution_id}"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = requests.get(
            api_url, auth=(username, password), verify=VERIFY,
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            write_failure_message(response)
            return None

        request_info = response.json()["request"]
        status = request_info.get("status")

        if status == "failed":
            error_message = request_info["output_params"]["errors"]
            raise RuntimeError(f"API request failed: {error_message}")

        if status == "finished":
            resources = request_info.get(
                "output_params", {}
            ).get("resources") or []
            if resources and resources[0].get("id"):
                update_dataset_metadata(
                    resources[0]["id"],
                    {
                        "advertised": False,
                        "is_published": False,
                        "category": (categories or {}).get(taxonomy),
                        "date": date_created,
                    },
                )
            return

        time.sleep(interval)

    raise TimeoutError(
        f"Upload {execution_id} did not finish within {timeout}s"
    )


def load_failed_uploads(path: str = FAILURE_LOG_PATH) -> set:
    """Read the set of files that failed during a previous run."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, 'r') as log_file:
            return set(json.load(log_file))
    except (OSError, ValueError) as e:
        print(f"Could not read failure log {path}: {e}")
        return set()


def save_failed_uploads(failed: set, path: str = FAILURE_LOG_PATH) -> None:
    """Persist the set of files that still need re-uploading."""
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, 'w') as log_file:
            json.dump(sorted(failed), log_file, indent=2)
    except OSError as e:
        print(f"Could not write failure log {path}: {e}")


def order_retries_first(dataset_files: list, failed: set) -> list:
    """Move previously failed files to the front of the upload order."""
    retries = [f for f in dataset_files if f in failed]
    remaining = [f for f in dataset_files if f not in failed]
    return retries + remaining


def process_batch(batch, categories, failed=None, consecutive_failures=0):
    """Upload a batch of dataset files.

    Args:
        batch: Dataset file paths to upload.
        categories: Mapping of taxonomy key to GeoNode category id.
        failed: Mutable set tracking files that still need re-uploading.
        consecutive_failures: Failure streak carried in from earlier batches.

    Returns:
        The trailing consecutive-failure count after this batch.

    Raises:
        UploadCircuitBreaker: After MAX_CONSECUTIVE_FAILURES failures in a row.
    """
    if failed is None:
        failed = set()

    for dataset_file in batch:
        try:
            basename = os.path.basename(dataset_file)
            date_part = basename.split('_')[-1].replace('.tif', '')
            date_created = f"{date_part[:4]}-{date_part[4:6]}-01"

            print(f"Uploading {basename} to GeoNode...")
            execution_id = upload_to_geonode(dataset_file)
            taxonomy = dataset_file.split('/')[-2]
            tracking_upload_progress(
                execution_id=execution_id,
                taxonomy=taxonomy.lower(),
                categories=categories,
                date_created=date_created
            )
            failed.discard(dataset_file)
            consecutive_failures = 0
        except Exception as e:
            print(f"Error uploading {dataset_file}: {e}")
            failed.add(dataset_file)
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                raise UploadCircuitBreaker(
                    f"{consecutive_failures} uploads failed in a row - "
                    "GeoNode or GeoServer is likely down"
                )

    return consecutive_failures


def run_upload(dataset_files, categories, batch_size=5, batch_delay=5):
    """Upload files in batches, tracking failures and tripping the breaker.

    Returns:
        True when every file uploaded, False when the run was aborted early.
    """
    failed = load_failed_uploads()
    if failed:
        print(f"Retrying {len(failed)} previously failed upload(s) first.")
        dataset_files = order_retries_first(dataset_files, failed)

    total_files = len(dataset_files)
    total_batches = (total_files + batch_size - 1) // batch_size
    consecutive_failures = 0
    aborted = False

    try:
        for i in range(0, total_files, batch_size):
            batch_num = (i // batch_size) + 1
            batch = dataset_files[i:i + batch_size]

            print(
                f"\n=== Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} files) ==="
            )
            consecutive_failures = process_batch(
                batch, categories, failed, consecutive_failures
            )

            # Add delay between batches (but not after the last batch)
            if i + batch_size < total_files:
                print(f"\nWaiting {batch_delay} seconds before next batch...")
                time.sleep(batch_delay)
    except UploadCircuitBreaker as e:
        print(f"\n=== Aborting run: {e} ===")
        aborted = True
    finally:
        save_failed_uploads(failed)

    if failed:
        print(
            f"\n{len(failed)} file(s) recorded in {FAILURE_LOG_PATH}; "
            "the next run retries them first."
        )
    return not aborted


def main():
    categories = get_categories(f"{geonode_url}/api/categories/")
    # Get limit from env var (default: None = upload all)
    limit_str = os.getenv("UPLOAD_RECENT_LIMIT")
    limit = int(limit_str) if limit_str else None
    dataset_files = get_recent_files(limit=limit)

    if not run_upload(dataset_files, categories):
        raise SystemExit(1)

    print("\n=== All batches completed ===")


if __name__ == '__main__':
    main()
