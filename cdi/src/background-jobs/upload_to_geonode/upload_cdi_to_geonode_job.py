import os
from upload_to_geonode_job import get_categories
from upload_to_geonode_job import run_upload

geonode_url = os.getenv("GEONODE_URL")
username = os.getenv("GEONODE_USERNAME")
password = os.getenv("GEONODE_PASSWORD")
dataset_path = "../../output_data/GeoTiffs/CDI"
dataset_type = ".tif"


def get_dataset_between(start, end):
    dataset_files = []
    # Check if the dataset path exists
    if not os.path.exists(dataset_path):
        print("Dataset path does not exist.")
        return dataset_files
    for root, dirs, files in os.walk(dataset_path):
        for file in files:
            if file.endswith(dataset_type):
                # Extract the date part from the filename
                date_part = file.split('_')[-1].replace('.tif', '')
                if start <= date_part <= end:
                    dataset_files.append(os.path.join(root, file))
    return dataset_files


def main():
    # Get all CDI files without date range restriction
    dataset_files = []
    if not os.path.exists(dataset_path):
        print("Dataset path does not exist.")
        return
    for root, _, files in os.walk(dataset_path):
        for file in files:
            if file.endswith(dataset_type):
                dataset_files.append(os.path.join(root, file))

    try:
        categories = get_categories(f"{geonode_url}/api/categories/")
        if not run_upload(dataset_files, categories):
            raise SystemExit(1)
        print("\n=== All batches completed ===")
    except SystemExit:
        raise
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
