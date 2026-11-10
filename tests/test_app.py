import unittest
from copy import deepcopy
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.app import activities, app


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.activities_patch = patch.dict(activities, deepcopy(activities), clear=True)
        self.activities_patch.start()
        self.addCleanup(self.activities_patch.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.url = "/activities/Chess%20Club/unregister"
        self.email = "michael@mergington.edu"

    def test_unregister_removes_only_selected_participant(self):
        original = deepcopy(activities)
        response = self.client.delete(self.url, params={"email": self.email})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"message": f"Unregistered {self.email} from Chess Club"},
        )
        original["Chess Club"]["participants"].remove(self.email)
        self.assertEqual(self.client.get("/activities").json(), original)

    def test_unregister_unknown_activity(self):
        original = deepcopy(activities)
        response = self.client.delete(
            "/activities/Unknown/unregister", params={"email": self.email}
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Activity not found"})
        self.assertEqual(activities, original)

    def test_unregister_unknown_participant(self):
        original = deepcopy(activities)
        response = self.client.delete(
            self.url, params={"email": "not-registered@mergington.edu"}
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Student not signed up"})
        self.assertEqual(activities, original)

    def test_unregister_requires_email(self):
        self.assertEqual(self.client.delete(self.url).status_code, 422)

    def test_last_participant_can_be_removed_and_signup_again(self):
        email = "student+art@mergington.edu"
        signup_url = "/activities/Art%20Club/signup"
        unregister_url = "/activities/Art%20Club/unregister"

        self.assertEqual(
            self.client.post(signup_url, params={"email": email}).status_code, 200
        )
        self.assertEqual(
            self.client.post(signup_url, params={"email": email}).status_code, 400
        )
        self.assertEqual(
            self.client.delete(unregister_url, params={"email": email}).status_code,
            200,
        )
        self.assertEqual(activities["Art Club"]["participants"], [])
        self.assertEqual(
            self.client.delete(unregister_url, params={"email": email}).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(signup_url, params={"email": email}).status_code, 200
        )


if __name__ == "__main__":
    unittest.main()
