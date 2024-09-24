# Bazarr Log Error Handler

This script retrieves Bazarr logs, identifies errors, and attempts to either repair, delete, or remux corrupted files. The script supports both command-line arguments and environment variables, including the use of a `.env` file for storing sensitive data such as API keys for Sonarr and Radarr.

## Features

- **Error Detection**: Parses Bazarr logs to identify errors.
- **Error Handling**: Supports various actions like ignoring errors, blacklisting movies, rescanning, and remuxing files.
- **Integration with Sonarr and Radarr**: Uses API keys to interact with Sonarr and Radarr for rescanning and blacklisting.
- **Command-line and Environment Variable Support**: Can be configured using command-line arguments or environment variables.

## Requirements

- Python 3.6+
- `requests` library
- `python-dotenv` library
- `ffmpeg` installed and available in the system PATH

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/bazarr_log_error_handler.git
    cd bazarr_log_error_handler
    ```

2. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the root directory and add your API keys and other configurations:
    ```env
    BAZARR_CONTAINER=bazarr
    SONARR_HOST=http://localhost:8989
    SONARR_KEY=your_sonarr_api_key
    RADARR_HOST=http://localhost:7878
    RADARR_KEY=your_radarr_api_key
    ```

## Usage

You can run the script using command-line arguments or rely on the `.env` file for configuration.

### Command-line Arguments

```sh
python docker_log_watcher.py --bazarr_container=bazarr \
    --sonarr_host=http://localhost:8989 --sonarr_key=SONARR_API_KEY \
    --radarr_host=http://localhost:7878 --radarr_key=RADARR_API_KEY --debug
```

### Environment Variables

If you have set up the `.env` file, you can simply run:

```sh
python docker_log_watcher.py
```

### Available Arguments

- `--bazarr_container`: Bazarr container name (default: value from `.env` file)
- `--sonarr_host`: Sonarr host URL (default: value from `.env` file)
- `--sonarr_key`: Sonarr API key (default: value from `.env` file)
- `--radarr_host`: Radarr host URL (default: value from `.env` file)
- `--radarr_key`: Radarr API key (default: value from `.env` file)
- `--debug`: Enable debug logging
- `--super-debug`: Enable super debug logging to show file processing before deduplication
- `--verbose-debug`: Enable verbose debug logging to show all details

## Example

To run the script with debug logging enabled:

```sh
python docker_log_watcher.py --debug
```

## Error Handling Rules

The script uses predefined rules to handle different types of errors found in the Bazarr logs. These rules are defined in the `ERROR_RULES` dictionary within the script. Each rule specifies an error pattern and the corresponding actions to take.

### Example Rule

```python
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
}
```

In this example, if the error message matches the pattern, the script will attempt to repair the file. If the repair is successful, the original file will be deleted. If the repair fails, the script will attempt to remux the file. If the remux is successful, the original file will be deleted; otherwise, the file will be replaced.

## Logging

The script uses Python's built-in logging module to log messages. The log level can be configured using the `--debug`, `--super-debug`, and `--verbose-debug` command-line arguments.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## License

This project is licensed under the MIT License.
