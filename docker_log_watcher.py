#!/usr/bin/env python3

"""
Bazarr Log Error Handler Script

This script retrieves Bazarr logs, identifies errors, and attempts to either
repair, delete, or remux corrupted files. The script supports both command-line
arguments and environment variables, including the use of a `.env` file for
storing sensitive data such as API keys for Sonarr and Radarr.

Usage:
    $ python bazarr_error_handler.py --bazarr_container=bazarr --sonarr_host=http://localhost:8989 --sonarr_key=SONARR_API_KEY --radarr_host=http://localhost:7878 --radarr_key=RADARR_API_KEY --debug
"""

import os
import subprocess
import argparse
import re
import logging
from pathlib import Path
from dotenv import load_dotenv
from radarr_api import handle_radarr_blacklist, handle_radarr_rescan
from sonarr_api import trigger_sonarr_rescan

# Load environment variables from .env file
load_dotenv()

# Error dictionary mapping error strings to actions
ERROR_RULES = [
    {"error": ".*Timeout.*", "action": [{"always": "IGNORE"}]},
    {"error": ".*+----.*-------+.*", "action": [{"always": "IGNORE"}]},
    {
        "error": ".*cannot insert movie.*because of (sqlite3.IntegrityError) UNIQUE constraint failed.*",
        "action": [{"always": "IGNORE"}],
    },
    {
        "error": ".*Error trying to get (series|movies|episodes|tags|episodeFiles|profiles) from (Sonarr|Radarr). Timeout.*",
        "action": [{"always": "IGNORE"}],
    },
    {"error": ".*UNIQUE constraint failed:.*", "action": [{"always": "IGNORE"}]},
    {
        "error": ".*is not a valid video extension.*",
        "action": ["BLACKLIST", {"REMUX": {"success": "DELETE", "fail": "REPLACE"}}],
    },
    {
        "error": ".*+-------------------------------------------------------+.*",
        "action": [{"always": "IGNORE"}],
    },
    {
        "error": ".*is not a valid video extension.*trying to get video information for this file.*",
        "action": ["BLACKLIST", {"REMUX": {"success": "DELETE", "fail": "REPLACE"}}],
    },
    {
        "error": ".*ffprobe cannot analyze this video file.*Could it be corrupted?.*",
        "action": [
            {
                "REPAIR": {
                    "success": "DELETE",
                    "fail": {"REMUX": {"success": "DELETE", "fail": "REPLACE"}},
                }
            }
        ],
    },
]

# Set up logging configuration
logger = logging.getLogger()


def mount_iso_and_remux(iso_path, output_path):
    """
    Mounts an ISO file, extracts the main video file, and remuxes it to an MKV format.

    Args:
        iso_path (str): The path to the ISO file.
        output_path (str): The path where the MKV file will be saved.

    Returns:
        bool: True if remuxing was successful, False otherwise.
    """
    # Create a mount point
    mount_point = "/mnt/iso"
    os.makedirs(mount_point, exist_ok=True)

    # Mount the ISO file
    mount_cmd = ["mount", "-o", "loop", iso_path, mount_point]
    logger.info(f"Mounting ISO: {iso_path}")
    try:
        subprocess.run(mount_cmd, check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to mount ISO: {iso_path}. Error: {e}")
        return False

    # Find the video file (assuming Blu-ray or DVD structure)
    # This example assumes Blu-ray structure; you might need to adjust for DVD (.VOB) files
    video_file = None
    stream_dir = os.path.join(mount_point, "BDMV/STREAM")
    if os.path.exists(stream_dir):
        for f in os.listdir(stream_dir):
            if f.endswith(".m2ts"):
                video_file = os.path.join(stream_dir, f)
                break

    if video_file is None:
        logger.error("No video file found in ISO.")
        try:
            subprocess.run(["umount", mount_point], check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Failed to unmount ISO: {iso_path}. Error: {e.stderr.decode().strip()}"
            )
        return False

    logger.info(f"Found video file: {video_file}")

    # Remux the video file to MKV
    remux_cmd = [
        "ffmpeg",
        "-i",
        video_file,
        "-c:v",
        "libx265",
        "-crf",
        "28",
        "-preset",
        "medium",
        "-c:a",
        "copy",
        output_path,
    ]

    logger.info(f"Running command: {' '.join(remux_cmd)}")
    try:
        subprocess.run(remux_cmd, check=True, stderr=subprocess.PIPE)
        logger.info(f"Remux successful: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Remux failed. Error: {e}")
    try:
        subprocess.run(["umount", mount_point], check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to unmount ISO: {iso_path}. Error: {e.stderr.decode().strip()}"
        )
        return False

    # Unmount the ISO
    logger.info(f"Unmounting ISO: {iso_path}")
    try:
        subprocess.run(["umount", mount_point], check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to unmount ISO: {iso_path}. Error: {e.stderr.decode().strip()}"
        )

    return True


def remux_file(file_path, delete_original=False):
    """
    Remux the given file to an MKV format using ffmpeg. If `delete_original` is True,
    the original file will be deleted after remuxing.

    Args:
        file_path (str): The path of the file to be remuxed.
        delete_original (bool): Whether to delete the original file after remuxing.

    Returns:
        bool: True if the remux process was successful, False otherwise.
    """
    logger.info(f"Attempting to remux file: {file_path}")
    if file_path.lower().endswith(".iso"):
        output_file = Path(file_path).with_suffix(".mkv")
        success = mount_iso_and_remux(file_path, str(output_file))
        if success and delete_original:
            logger.info(f"Deleting original ISO file: {file_path}")
            os.remove(file_path)
        return success

    output_file = Path(file_path).with_suffix("").name + "_h265.mkv"

    # Run ffmpeg command to remux the file
    cmd = [
        "ffmpeg",
        "-i",
        file_path,
        "-c:v",
        "libx265",
        "-crf",
        "28",
        "-preset",
        "medium",
        "-c:a",
        "copy",
        str(output_file),
    ]
    logger.debug(f"Running command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Remux successful: {output_file}")

        if delete_original:
            logger.info(f"Deleting original file: {file_path}")
            os.remove(file_path)

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Remux failed for file: {file_path}. Error: {e}")
        return False


def handle_file(file_path, actions, args):
    """
    Handles the file based on the provided actions. This could involve deleting,
    remuxing, or triggering Sonarr/Radarr to find a new copy.
    """
    logger.info(f"Handling file: {file_path}")
    try:
        file_size = Path(file_path).stat().st_size / (1024 * 1024)  # Get size in MB
        logger.debug(f"File size: {file_size:.2f} MB")
    except FileNotFoundError:
        if args.super_debug:
            logger.error(f"File not found: {file_path}")
        return

    valid_video_extensions = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".m4v"}
    duplicate_files = [
        file
        for file in Path(file_path).parent.glob("*")
        if file.suffix in valid_video_extensions
    ]

    if len(duplicate_files) > 1:
        smallest_file = min(duplicate_files, key=lambda f: f.stat().st_size)
        logger.info(
            f"Duplicate files found. Removing the smallest file: {smallest_file}"
        )
        delete_file(smallest_file)
        return

    for action in actions:
        if isinstance(action, dict):  # Conditional action like REMUX or REPAIR
            action_name, result = list(action.items())[0]
            logger.info(f"Executing action: {action_name}")

            if action_name == "REMUX":
                remux_success = remux_file(file_path)
                next_action = result["success"] if remux_success else result["fail"]
                logger.info(
                    f"Remux result: {'success' if remux_success else 'fail'}. Next action: {next_action}"
                )
                if next_action == "DELETE":
                    delete_file(file_path)
                elif next_action == "REPLACE":
                    delete_file(file_path)
                    handle_radarr_rescan(file_path, RADARR_HOST, RADARR_KEY)
                    trigger_sonarr_rescan(file_path, SONARR_HOST, SONARR_KEY)

        elif action == "BLACKLIST":
            handle_radarr_blacklist(file_path, RADARR_HOST, RADARR_KEY)
            trigger_sonarr_rescan(file_path, SONARR_HOST, SONARR_KEY)
            remux_file(file_path, delete_original=True)
        elif action == "REPLACE":
            handle_radarr_rescan(file_path, RADARR_HOST, RADARR_KEY)
        elif action == "IGNORE":
            logger.info(f"Ignoring error for file: {file_path}")


def delete_file(file_path):
    """
    Deletes the given file.
    """
    logger.info(f"Deleting file: {file_path}")
    try:
        os.remove(file_path)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")


def determine_action_for_error(error_cause):
    """
    Determines the action based on the error cause using the predefined ERROR_RULES.
    """
    for rule in ERROR_RULES:
        try:
            if re.search(rule["error"], error_cause):
                return rule["action"]
        except re.error as regex_error:
            logger.error(f"Error in regex for {rule['error']}: {regex_error}")
    return ["UNMATCHED"]


def parse_bazarr_logs(args):
    """
    Retrieve and parse Bazarr logs for error lines. Each error line is deduplicated
    by file name, and the error cause is extracted for further handling.
    """
    logger.info("Retrieving Bazarr logs...")
    cmd = f"docker logs {BAZARR_CONTAINER} 2>&1 | grep ':  ERROR'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error("Failed to retrieve logs from Bazarr container.")
        return {}

    logger.info("Bazarr logs retrieved, parsing errors...")
    error_lines = result.stdout.splitlines()

    error_pattern = r".+ERROR \(.+\) - BAZARR (.+) (.+)"
    deduped_errors = {}
    processed_files = set()

    for line in error_lines:
        if args.verbose_debug:
            logger.debug(f"Processing log line: {line}")

        # Skip lines with only dashes
        if "+-------------------------------------------------------+" in line:
            continue

        match = re.search(error_pattern, line)
        if match:
            error_cause, file_path = match.groups()
            file_path = file_path.split(" ")[-1].strip()
            logger.debug(f"Log Line: {line}")
            logger.debug(f"File Name: {file_path}")
            logger.debug(f"Error Cause: {error_cause}")

            if file_path not in processed_files:
                actions = determine_action_for_error(error_cause)
                if not (actions == [{"always": "IGNORE"}] and args.debug):
                    logger.debug(f"Action Planned: {actions}")
                deduped_errors[file_path] = {
                    "error_cause": error_cause,
                    "actions": actions,
                }
                processed_files.add(file_path)

    logger.info(f"Found {len(deduped_errors)} unique errors in Bazarr logs.")
    return deduped_errors


def main():
    """
    Main entry point for the Bazarr Log Error Handler script. This function handles argument
    parsing, environment variable setup, log retrieval, and error handling.
    """
    parser = argparse.ArgumentParser(description="Bazarr Log Error Handler")
    parser.add_argument(
        "--bazarr_container",
        type=str,
        default=os.getenv("BAZARR_CONTAINER"),
        help="Bazarr container name",
    )
    parser.add_argument(
        "--sonarr_host", type=str, default=os.getenv("SONARR_HOST"), help="Sonarr host"
    )
    parser.add_argument(
        "--sonarr_key", type=str, default=os.getenv("SONARR_KEY"), help="Sonarr API key"
    )
    parser.add_argument(
        "--radarr_host", type=str, default=os.getenv("RADARR_HOST"), help="Radarr host"
    )
    parser.add_argument(
        "--radarr_key", type=str, default=os.getenv("RADARR_KEY"), help="Radarr API key"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--super-debug",
        action="store_true",
        help="Enable super debug logging to show file processing before deduplication",
    )
    parser.add_argument(
        "--verbose-debug",
        action="store_true",
        help="Enable verbose debug logging to show all details",
    )
    args = parser.parse_args()

    if args.super_debug:
        log_level = logging.DEBUG
    elif args.verbose_debug:
        log_level = logging.DEBUG
    elif args.debug:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    global BAZARR_CONTAINER, SONARR_HOST, SONARR_KEY, RADARR_HOST, RADARR_KEY
    BAZARR_CONTAINER = args.bazarr_container
    SONARR_HOST = args.sonarr_host
    SONARR_KEY = args.sonarr_key
    RADARR_HOST = args.radarr_host
    RADARR_KEY = args.radarr_key

    if not all([BAZARR_CONTAINER, SONARR_HOST, SONARR_KEY, RADARR_HOST, RADARR_KEY]):
        logger.error("Missing required arguments or environment variables.")
        return

    logger.info("Starting Bazarr log analysis...")
    errors = parse_bazarr_logs(args)

    for file_path, data in errors.items():
        error_cause = data["error_cause"]
        actions = data["actions"]
        if args.debug:
            logger.debug(f"Actions Planned: {actions} for file: {file_path}")

        if "IGNORE" in actions:
            if args.debug:
                logger.info(f"Skipping error: {error_cause}")
        elif "UNMATCHED" in actions:
            logger.info(f"Unmatched error for file: {file_path}")
        else:
            handle_file(file_path, actions, args)

    logger.info("Bazarr log error handling completed.")


if __name__ == "__main__":
    main()
