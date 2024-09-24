import pytest
import requests
from unittest.mock import patch, MagicMock
from radarr_api import get_movie_id_from_radarr, trigger_radarr_rescan, blacklist_movie_in_radarr

@patch('radarr_api.requests.get')
def test_get_movie_id_from_radarr_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"path": "/data/movies/MovieName", "id": 1}]
    mock_get.return_value = mock_response
    result = get_movie_id_from_radarr('/data/movies/MovieName/movie.mkv', 'http://localhost:7878', 'fake_api_key')
    assert result == 1

@patch('radarr_api.requests.get')
def test_get_movie_id_from_radarr_failure(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response
    result = get_movie_id_from_radarr('/data/movies/MovieName/movie.mkv', 'http://localhost:7878', 'fake_api_key')
    assert result == None

@patch('radarr_api.requests.post')
def test_trigger_radarr_rescan_success(mock_post):
    mock_post.return_value.status_code = 201
    result = trigger_radarr_rescan(1, 'http://localhost:7878', 'fake_api_key')
    assert result == True

@patch('radarr_api.requests.post')
def test_trigger_radarr_rescan_failure(mock_post):
    mock_post.return_value.status_code = 500
    result = trigger_radarr_rescan(1, 'http://localhost:7878', 'fake_api_key')
    assert result == False

@patch('radarr_api.requests.get')
@patch('radarr_api.requests.put')
def test_blacklist_movie_in_radarr_success(mock_put, mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"qualityProfileId": 1, "path": "/data/movies/MovieName", "title": "MovieName", "rootFolderPath": "/data/movies", "minimumAvailability": "announced", "year": 2020, "tmdbId": 12345, "titleSlug": "moviename", "images": []}))
    mock_put.return_value = MagicMock(status_code=200)
    result = blacklist_movie_in_radarr(1, 'http://localhost:7878', 'fake_api_key')
    assert result == True

@patch('radarr_api.requests.get')
@patch('radarr_api.requests.put')
def test_blacklist_movie_in_radarr_failure(mock_put, mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=MagicMock(return_value={"qualityProfileId": 1, "path": "/data/movies/MovieName", "title": "MovieName", "rootFolderPath": "/data/movies", "minimumAvailability": "announced", "year": 2020, "tmdbId": 12345, "titleSlug": "moviename", "images": []}))
    mock_put.return_value = MagicMock(status_code=500)
    result = blacklist_movie_in_radarr(1, 'http://localhost:7878', 'fake_api_key')
    assert result == False
