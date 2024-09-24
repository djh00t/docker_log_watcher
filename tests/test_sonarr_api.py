import pytest
import requests
from unittest.mock import patch, MagicMock
from sonarr_api import trigger_sonarr_rescan

@patch('sonarr_api.requests.post')
def test_trigger_sonarr_rescan_success(mock_post):
    mock_post.return_value.status_code = 200
    result = trigger_sonarr_rescan('/data/tv/SeriesName/Season/episode.mkv', 'http://localhost:8989', 'fake_api_key')
    assert result == True

@patch('sonarr_api.requests.post')
def test_trigger_sonarr_rescan_failure(mock_post):
    mock_post.return_value.status_code = 500
    result = trigger_sonarr_rescan('/data/tv/SeriesName/Season/episode.mkv', 'http://localhost:8989', 'fake_api_key')
    assert result == False
