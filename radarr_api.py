import requests
import logging
from pathlib import Path

logger = logging.getLogger()


def get_movie_id_from_radarr(file_path, radarr_host, radarr_key):
    """
    Get the Radarr movie ID based on the movie folder path.
    Radarr requires a movie ID to trigger commands such as Rescan or Blacklist.
    """
    movie_folder = Path(file_path).parent
    url = f"{radarr_host}/api/v3/movie"
    headers = {"X-Api-Key": radarr_key}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        movies = response.json()
        for movie in movies:
            if movie["path"] == str(movie_folder):
                logger.info(f"Found movie ID {movie['id']} for folder: {movie_folder}")
                return movie["id"]
        logger.error(f"Movie not found for folder: {movie_folder}")
    else:
        logger.error(
            f"Failed to retrieve movies from Radarr. Status Code: {response.status_code}, Response: {response.text}"
        )

    return None


def trigger_radarr_rescan(movie_id, radarr_host, radarr_key):
    """
    Trigger Radarr to rescan the movie based on the movie ID.
    """
    url = f"{radarr_host}/api/v3/command"
    headers = {"X-Api-Key": radarr_key}
    payload = {"name": "RescanMovie", "movieId": movie_id, "trigger": "manual"}

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        logger.info(f"Rescan successfully triggered for movie ID: {movie_id}")
        return True
    else:
        logger.error(
            f"Radarr Rescan API call failed for movie ID: {movie_id}. Status Code: {response.status_code}, Response: {response.text}"
        )
        return False


import time


def blacklist_movie_in_radarr(movie_id, radarr_host, radarr_key, retries=3, delay=5):
    """
    Blacklist a movie by setting its `monitored` status to False in Radarr.
    Requires the movie's existing QualityProfileId and other attributes.

    Args:
        movie_id (int): The Radarr movie ID.
        radarr_host (str): The Radarr host URL.
        radarr_key (str): The API key for Radarr.
    """
    # Get the existing movie details first to retrieve the current QualityProfileId and other required fields
    url = f"{radarr_host}/api/v3/movie/{movie_id}"
    headers = {"X-Api-Key": radarr_key}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        movie_data = response.json()
        quality_profile_id = movie_data["qualityProfileId"]
        logger.info(
            f"Retrieved QualityProfileId {quality_profile_id} for movie ID {movie_id}"
        )

        # Now update the movie, setting `monitored` to False (blacklisting)
        # Ensure the path is included in the update payload
        update_payload = {
            "path": movie_data["path"],
            "title": movie_data["title"],
            "qualityProfileId": quality_profile_id,
            "monitored": False,  # Blacklist the movie
            "rootFolderPath": movie_data["rootFolderPath"],
            "minimumAvailability": movie_data["minimumAvailability"],
            "addOptions": {
                "ignoreEpisodesWithFiles": movie_data.get("addOptions", {}).get(
                    "ignoreEpisodesWithFiles", False
                ),
                "ignoreEpisodesWithoutFiles": movie_data.get("addOptions", {}).get(
                    "ignoreEpisodesWithoutFiles", False
                ),
            },
            "year": movie_data["year"],
            "tmdbId": movie_data["tmdbId"],
            "titleSlug": movie_data["titleSlug"],
            "images": movie_data["images"],
            "id": movie_id,
        }

        for attempt in range(retries):
            update_response = requests.put(url, json=update_payload, headers=headers)

            if update_response.status_code == 200:
                logger.info(f"Movie ID {movie_id} successfully blacklisted in Radarr.")
                return True
            elif update_response.status_code == 202:
                logger.warning(
                    f"Blacklist request accepted but not processed for movie ID {movie_id}. Retrying in {delay} seconds..."
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Failed to blacklist movie ID {movie_id} in Radarr. Status Code: {update_response.status_code}, Response: {update_response.text}"
                )
                return False

        logger.error(
            f"Exceeded maximum retries for blacklisting movie ID {movie_id} in Radarr."
        )
        return False
    else:
        logger.error(
            f"Failed to retrieve movie ID {movie_id} details. Status Code: {response.status_code}, Response: {response.text}"
        )
        return False


def handle_radarr_blacklist(file_path, radarr_host, radarr_key):
    """
    Handle the process of blacklisting a movie in Radarr.
    """
    movie_id = get_movie_id_from_radarr(file_path, radarr_host, radarr_key)
    if movie_id:
        blacklist_movie_in_radarr(movie_id, radarr_host, radarr_key)


def handle_radarr_rescan(file_path, radarr_host, radarr_key):
    """
    Handle the process of rescanning a movie in Radarr.
    """
    movie_id = get_movie_id_from_radarr(file_path, radarr_host, radarr_key)
    if movie_id:
        trigger_radarr_rescan(movie_id, radarr_host, radarr_key)
