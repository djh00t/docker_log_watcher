import pytest
import subprocess
from unittest.mock import patch, MagicMock
import logging
from docker_log_watcher import remux_file, delete_file, determine_action_for_error, parse_bazarr_logs

logger = logging.getLogger()

@patch('docker_log_watcher.subprocess.run')
def test_remux_file_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    result = remux_file('/path/to/video.mkv')
    assert result == True

@patch('docker_log_watcher.subprocess.run')
def test_remux_file_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1)
    result = remux_file('/path/to/video.mkv')
    assert result == False

@patch('docker_log_watcher.os.remove')
def test_delete_file(mock_remove):
    delete_file('/path/to/video.mkv')
    mock_remove.assert_called_once_with('/path/to/video.mkv')

def test_determine_action_for_error():
    error_cause = "ffprobe cannot analyze this video file. Could it be corrupted?"
    actions = determine_action_for_error(error_cause)
    assert actions == [{'REPAIR': {'success': 'DELETE', 'fail': {'REMUX': {'success': 'DELETE', 'fail': 'REPLACE'}}}}]

@patch('docker_log_watcher.subprocess.run')
def test_parse_bazarr_logs(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="2023-09-24 17:40:55,123 - ERROR - BAZARR ffprobe cannot analyze this video file. Could it be corrupted? /path/to/video.mkv\n")
    logger.debug("Mocked subprocess.run to return Bazarr log with error")
    args = MagicMock()
    args.verbose_debug = False
    global BAZARR_CONTAINER
    BAZARR_CONTAINER = "bazarr"
    errors = parse_bazarr_logs(args, BAZARR_CONTAINER)
    assert '/path/to/video.mkv' in errors
    assert errors['/path/to/video.mkv']['error_cause'] == 'ffprobe cannot analyze this video file. Could it be corrupted?'
