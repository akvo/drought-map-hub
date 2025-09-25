import os
import json
import requests

# Get the root directory of the project (cdi folder)
script_dir = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

geonode_url = os.getenv("GEONODE_URL")
username = os.getenv("GEONODE_USERNAME")
password = os.getenv("GEONODE_PASSWORD")
dataset_path = os.path.join(root_path, "output_data", "GeoTiffs")
dataset_type = ".tif"


def get_categories(api_url, file_name="geonode_category.json"):
    try:
        # Fetch data from the API
        response = requests.get(api_url)
        # Will raise an error for 4xx or 5xx status codes
        response.raise_for_status()

        selected_categories = [
            "cdi-raster-map",
            "spi-raster-map",
            "ndvi-raster-map",
            "lst-raster-map"
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
    api_url = f"{geonode_url}api/v2/uploads/upload?format=json"
    files = {
        "base_file": open(base_file_path, "rb"),
    }
    if xml_file_path:
        files["xml_file"] = open(xml_file_path, "rb")
    if sld_file_path:
        files["sld_file"] = open(sld_file_path, "rb")
    data = {
        "store_spatial_files": False,
        "overwrite_existing_layer": True,
        "skip_existing_layers": False,
    }
    response = requests.post(
        api_url,
        auth=(username, password),
        files=files,
        data=data
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


def get_recent_files(limit=5):
    dataset_files = []

    for root, dirs, files in os.walk(dataset_path):
        for file in files:
            if file.endswith(dataset_type):
                file_path = os.path.join(root, file)
                dataset_files.append((file_path, os.path.getmtime(file_path)))

    # Sort files by modification time (newest first)
    dataset_files.sort(key=lambda x: x[1], reverse=True)

    # Extract file paths, limited to `limit`
    recent_files = [file[0] for file in dataset_files[:limit]]

    # Raise an error if no files are found
    if not recent_files:
        raise FileNotFoundError(
            f"No files with extension '{dataset_type}' found in {dataset_path}"
        )

    return recent_files


def update_dataset_metadata(dataset_id, metadata):
    api_url = f"{geonode_url}api/v2/datasets/{dataset_id}"
    response = requests.patch(
        api_url,
        auth=(username, password),
        json=metadata
    )
    if response.status_code == 200:
        print("Dataset successfully uploaded!")
    else:
        write_failure_message(response)


def tracking_upload_progress(
    execution_id: int,
    taxonomy: str,
    categories: object,
    date_created: str = None
):
    if not execution_id:
        return
    api_url = f"{geonode_url}api/v2/executionrequest/{execution_id}"
    response = requests.get(api_url, auth=(username, password))
    if response.status_code == 200:
        json_response = response.json()["request"]
        if json_response["status"] == "failed":
            error_message = json_response["output_params"]["errors"]
            raise RuntimeError(f"API request failed: {error_message}")
        if not json_response["finished"]:
            tracking_upload_progress(
                execution_id,
                taxonomy,
                categories,
                date_created,
            )
        if json_response["status"] == "finished":
            dataset = json_response.get("output_params").get("resources")[0]
            if dataset.get("id"):
                update_dataset_metadata(
                    dataset["id"],
                    {
                        "advertised": False,
                        "is_published": False,
                        "category": categories.get(taxonomy),
                        "date": date_created,
                    },
                )
    else:
        write_failure_message(response)
        return None


def main():
    categories = get_categories(f"{geonode_url}api/categories/")
    dataset_files = get_recent_files()
    for dataset_file in dataset_files:
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


if __name__ == '__main__':
    main()
