import io
import os
import shutil
import tarfile
from pathlib import Path

import requests

# Set the GitHub API URL for Swagger UI releases
GITHUB_API_URL = "https://api.github.com/repos/swagger-api/swagger-ui/releases/latest"

# Define where to store the downloaded files
DOWNLOAD_DIR = Path("fastapi_swagger/resources")

# File to store the latest release tag
LATEST_RELEASE_FILE = "latest_release.txt"


def get_latest_release():
    response = requests.get(GITHUB_API_URL)
    if response.status_code == 200:
        release_data = response.json()
        return release_data["tag_name"], release_data["tarball_url"]
    else:
        raise Exception("Failed to fetch release data from GitHub.")


def download_assets(tarball_url):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    else:
        shutil.rmtree(DOWNLOAD_DIR)
        os.makedirs(DOWNLOAD_DIR)

    response = requests.get(tarball_url, stream=True)
    if response.status_code == 200:
        with io.BytesIO(response.content) as f:
            tar = tarfile.open(fileobj=f)
            filtered = []
            for m in tar.getmembers():
                as_path = Path(m.path)
                if (
                    as_path.parent
                    and as_path.parent.name == "dist"
                    and as_path.name
                    in ("favicon-32x32.png", "swagger-ui.css", "swagger-ui-bundle.js")
                ):
                    filtered.append(m)
            tar.extractall(DOWNLOAD_DIR, members=filtered)
        # Now it like
        # swagger-ui
        # ├── swagger-apr-swagger-ui-*
        # │   ├── dist
        # │   │   ├── favicon-32x32.png
        # │   │   ├── swagger-ui.css
        # │   │   └── swagger-ui-bundle.js

        # Need to be
        # swagger-ui
        # ├── favicon-32x32.png
        # ├── swagger-ui.css
        # ├── swagger-ui-bundle.js
        # ├── __init__.py

        # Move the files to the root of the DOWNLOAD_DIR
        for f in DOWNLOAD_DIR.rglob("*"):
            if f.is_file():
                shutil.move(f, DOWNLOAD_DIR)
        # Remove the extracted directory
        for d in DOWNLOAD_DIR.rglob("swagger-api-swagger-ui-*"):
            shutil.rmtree(d)
        # Add __init__.py
        Path(DOWNLOAD_DIR / "__init__.py").touch()
    else:
        raise Exception("Failed to download assets from GitHub.")


def check_and_download_new_release():
    latest_release, tarball_url = get_latest_release()
    print(f"Latest release: {latest_release}")

    if os.path.exists(LATEST_RELEASE_FILE):
        with open(LATEST_RELEASE_FILE, "r") as f:
            stored_release = f.read().strip()
    else:
        stored_release = None

    if latest_release != stored_release:
        print("New release detected. Downloading assets...")
        download_assets(tarball_url)
        with open(LATEST_RELEASE_FILE, "w") as f:
            f.write(latest_release)
        print("Assets downloaded and release version updated.")
        return True, latest_release
    else:
        print("No new release detected.")
        return False, stored_release


if __name__ == "__main__":
    updated, version = check_and_download_new_release()
    env_file = os.getenv("GITHUB_ENV")
    if env_file:
        with open(env_file, "a") as myfile:
            myfile.write("SWAGGER_UI_VERSION=" + version + "\n")
            updated_ = "true" if updated else "false"
            myfile.write("SWAGGER_UI_UPDATED=" + updated_ + "\n")
