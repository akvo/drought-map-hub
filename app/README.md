# eswatini-droughtmap-hub

Eswatini Droughtmap Hub

[![Coverage Status](https://coveralls.io/repos/github/akvo/eswatini-droughtmap-hub/badge.svg?branch=main)](https://coveralls.io/github/akvo/eswatini-droughtmap-hub?branch=main) [![DBdocs](https://img.shields.io/website?url=http%3A%2F%2Fdbdocs.io%2Fakvo%2Feswatini-droughtmap-hub&style=flat&logo=docsdotrs&logoColor=%23fff&label=dbdocs&labelColor=%230246cc&color=%235e5e5e&link=http%3A%2F%2Fdbdocs.io%2Fakvo%2Feswatini-droughtmap-hub)](https://dbdocs.io/akvo/eswatini-droughtmap-hub)

# **Setup GeoNode Locally**

1. **Clone and Install GeoNode**
   You can either clone this default repository or use the [GeoNode Project repository](https://github.com/GeoNode/geonode-project) to generate a customized GeoNode.

   ```bash
   git clone https://github.com/akvo/geonode-project.git
   cd geonode
   ```

2. **Set Up Local Environment**
   Install the necessary dependencies (Docker is the recommended approach for ease of setup):

   ```bash
   docker-compose up -d
   ```

3. **Set Environment Variables**
   Update your `.env` file or export the following environment variables:

   ```bash
   export GEONODE_BASE_URL="http://<your_ip_address>"
   export GEONODE_ADMIN_USERNAME="<your_admin_username_or_email>"
   export GEONODE_ADMIN_PASSWORD="<your_admin_password>"
   ```

   Replace `<your_ip_address>`, `<your_admin_username_or_email>`, and `<your_admin_password>` with your desired values.

4. **Access GeoNode**
   Open GeoNode in your browser at `http://<your_ip_address>` and log in using the admin credentials.

5. **Add a New Dataset Category**
   - Navigate to **Admin Panel** → **Base** → **Metadata Topic Categories** → **Add topic category**.
    > PATH URL: [/[locale]/admin/base/topiccategory/add/](/admin/base/topiccategory/add/)
   - Fill in the details as follows:
     - **Identifier**: `cdi-raster-map`
     - **Description [en]**: `CDI Raster Map`
   - Save the category.

---

## **Configure Eswatini Droughtmap Hub**

1. **Set Environment Variables**
   In the Eswatini Droughtmap Hub project, update your environment variables file to include:

   ```bash
   GEONODE_BASE_URL="http://<your_ip_address>"
   GEONODE_ADMIN_USERNAME="<your_admin_username_or_email>"
   GEONODE_ADMIN_PASSWORD="<your_admin_password>"
   ```

2. **Restart the Droughtmap Hub**
   Restart the application to apply the updated environment variables.

---

## **Test the Setup**

1. **Upload a Dataset to GeoNode**

   - Log in to GeoNode as an admin.
   - Upload a raster (*.tif, *.tiff) dataset.
   - Set its category to `cdi-raster-map`.

2. **Verify in Eswatini Droughtmap Hub**

   - Log in to the Droughtmap Hub as an admin.
   - Navigate to `/publications`.
   - If configured correctly, the list of datasets from GeoNode should appear, allowing you to start a new publication.

3. **Troubleshooting**
   - If no datasets are visible:
     - Double-check the environment variable values in the Droughtmap Hub.
     - Verify that GeoNode is accessible and the dataset category is correctly assigned.
   - Open a new issue in the relevant repository if the problem persists.

# **Running `check_overdue_reviews` Command**
The `check_overdue_reviews` command is used to **check all CDI Map reviews** in the system. If a review’s **due date has passed**, the system will **automatically send email notifications** to all related reviewers.

This ensures that no review is missed and all pending actions are **properly tracked**.

---

## **🔹 Example: Run Every Day at Midnight**
```bash
0 0 * * * /usr/bin/python3 /backend/manage.py check_overdue_reviews >> /home/user/logs/check_overdue_reviews.log 2>&1
```
**Explanation:**
- Checks for overdue CDI Map reviews at **midnight** every day.
- Sends email notifications to **all reviewers whose reviews are overdue**.
- Logs the output to `/home/user/logs/check_overdue_reviews.log`.