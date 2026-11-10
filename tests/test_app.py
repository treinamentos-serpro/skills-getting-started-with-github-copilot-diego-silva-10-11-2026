from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    original_activities = deepcopy(activities)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        activities.clear()
        activities.update(original_activities)


def test_root_redirects_to_static_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_all_activities(client):
    expected_activities = deepcopy(activities)

    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == expected_activities


def test_unregister_removes_only_selected_participant(client):
    email = "michael@mergington.edu"
    expected_activities = deepcopy(activities)

    response = client.delete(
        "/activities/Chess%20Club/unregister", params={"email": email}
    )
    expected_activities["Chess Club"]["participants"].remove(email)

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from Chess Club",
    }
    assert client.get("/activities").json() == expected_activities


def test_unregister_unknown_activity_does_not_change_activities(client):
    original_activities = deepcopy(activities)

    response = client.delete(
        "/activities/Unknown/unregister",
        params={"email": "michael@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert activities == original_activities


def test_unregister_unknown_participant_does_not_change_activities(client):
    original_activities = deepcopy(activities)

    response = client.delete(
        "/activities/Chess%20Club/unregister",
        params={"email": "not-registered@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Student not signed up"}
    assert activities == original_activities


def test_unregister_requires_email(client):
    response = client.delete("/activities/Chess%20Club/unregister")

    assert response.status_code == 422


def test_last_participant_can_be_removed_and_sign_up_again(client):
    email = "student+art@mergington.edu"
    signup_url = "/activities/Art%20Club/signup"
    unregister_url = "/activities/Art%20Club/unregister"

    signup_response = client.post(signup_url, params={"email": email})
    duplicate_signup_response = client.post(signup_url, params={"email": email})
    unregister_response = client.delete(unregister_url, params={"email": email})
    participants_after_unregister = deepcopy(activities["Art Club"]["participants"])
    repeated_unregister_response = client.delete(
        unregister_url, params={"email": email}
    )
    signup_again_response = client.post(signup_url, params={"email": email})

    assert signup_response.status_code == 200
    assert duplicate_signup_response.status_code == 400
    assert unregister_response.status_code == 200
    assert participants_after_unregister == []
    assert repeated_unregister_response.status_code == 404
    assert signup_again_response.status_code == 200
