import os
from upload_to_geonode_job import get_categories
from upload_to_geonode_job import tracking_upload_progress
from upload_to_geonode_job import upload_to_geonode

# Get the root directory of the project (cdi folder)
script_dir = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

geonode_url = os.getenv("GEONODE_URL")
username = os.getenv("GEONODE_USERNAME")
password = os.getenv("GEONODE_PASSWORD")
dataset_path = os.path.join(root_path, "output_data", "GeoTiffs", "CDI")
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
    dataset_files = get_dataset_between("202201", "202501")
    try:
        categories = get_categories(f"{geonode_url}api/categories/")
        for dataset_file in dataset_files:
            basename = os.path.basename(dataset_file)
            date_part = basename.split('_')[-1].replace('.tif', '')
            # convert date part to datetime object: 202201 -> 2022-01-01
            date_created = f"{date_part[:4]}-{date_part[4:6]}-01"

            print(f"Uploading {date_created} to GeoNode...")
            execution_id = upload_to_geonode(dataset_file)
            taxonomy = dataset_file.split('/')[-2]
            tracking_upload_progress(
                execution_id=execution_id,
                taxonomy=taxonomy.lower(),
                categories=categories,
                date_created=date_created
            )

    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
