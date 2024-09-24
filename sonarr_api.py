import requests
import logging
from pathlib import Path

logger = logging.getLogger()

def trigger_sonarr_rescan(file_path, sonarr_host, sonarr_key):
    """
    Trigger Sonarr to find a new copy of the TV show episode and blacklist the
    corrupted version. Uses the /api/v3/command endpoint with the command name
    'RescanSeries'.
    """
    logger.info(f"Triggering Sonarr for file: {file_path}")
    
    # Sonarr expects the path to the series folder, not individual files
    series_folder = Path(file_path).parent.parent  # Assumes folder structure /data/tv/SeriesName/Season/episode.mkv

    url = f"{sonarr_host}/api/v3/command"
    headers = {"X-Api-Key": sonarr_key}
    payload = {
        "name": "RescanSeries",
        "path": str(series_folder)
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        logger.info(f"Sonarr successfully triggered for file: {file_path}")
        return True
    else:
        logger.error(f"Sonarr API call failed for file: {file_path}. Status Code: {response.status_code}, Response: {response.text}")
        return False
