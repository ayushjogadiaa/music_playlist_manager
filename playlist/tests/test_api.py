"""
Django TestCase suite for the Playlist API Endpoints.

Verifies:
- Seeding sample data
- Endpoint success paths (state, play, next, prev, insert, delete, move)
- Invalid inputs and proper HTTP 400 / 404 error codes (never 500)
- Circular wrap-around navigation through the API
- Persistence of state across separate HTTP requests
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from playlist.models import Track, PlaylistState
from playlist.services import seed_sample_tracks


class TestPlaylistAPI(TestCase):
    """Test all JSON API views and contract enforcement."""

    def setUp(self):
        self.client = Client()
        seed_sample_tracks()

    def _post_json(self, url: str, data: dict):
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_get_state_success(self):
        """GET /api/state/ returns complete initial state."""
        response = self.client.get(reverse("api_state"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_tracks"], 5)
        self.assertIsNotNone(data["current_track"])
        self.assertEqual(data["current_track"]["title"], "Bohemian Rhapsody")
        self.assertEqual(len(data["tracks"]), 5)
        self.assertEqual(len(data["upcoming_tracks"]), 3)

    def test_next_and_wraparound_via_api(self):
        """POST /api/next/ navigates forward and wraps from tail to head."""
        # Initial is track 1 (Bohemian Rhapsody)
        # Advance 4 times to reach tail (track 5: Blinding Lights)
        for expected_title in ["Hotel California", "Billie Jean", "Shape of You", "Blinding Lights"]:
            res = self.client.post(reverse("api_next"))
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["current_track"]["title"], expected_title)

        # 5th next: Must wrap around to track 1 (Bohemian Rhapsody)
        res_wrap = self.client.post(reverse("api_next"))
        self.assertEqual(res_wrap.status_code, 200)
        self.assertEqual(res_wrap.json()["current_track"]["title"], "Bohemian Rhapsody")

    def test_prev_and_wraparound_via_api(self):
        """POST /api/prev/ on first track wraps backwards to the tail."""
        res = self.client.post(reverse("api_prev"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["current_track"]["title"], "Blinding Lights")

    def test_play_toggle_and_select_by_id(self):
        """POST /api/play/ toggles playback and selects specific tracks."""
        # Toggle play
        res1 = self._post_json(reverse("api_play"), {"is_playing": True})
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()["is_playing"])

        # Switch to track 3 (Billie Jean)
        track3 = Track.objects.get(position=3)
        res2 = self._post_json(reverse("api_play"), {"track_id": track3.id})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["current_track"]["id"], track3.id)
        self.assertEqual(res2.json()["current_track"]["title"], "Billie Jean")

        # Invalid track_id returns 404
        res_invalid = self._post_json(reverse("api_play"), {"track_id": 99999})
        self.assertEqual(res_invalid.status_code, 404)
        self.assertFalse(res_invalid.json()["success"])

    def test_insert_track_validation_and_success(self):
        """POST /api/insert/ validates inputs and persists new tracks."""
        # Missing title
        res_err1 = self._post_json(reverse("api_insert"), {
            "title": "",
            "artist": "Queen",
            "duration": 200
        })
        self.assertEqual(res_err1.status_code, 400)

        # Non-numeric duration
        res_err2 = self._post_json(reverse("api_insert"), {
            "title": "Yesterday",
            "artist": "The Beatles",
            "duration": "invalid"
        })
        self.assertEqual(res_err2.status_code, 400)

        # Out-of-range position
        res_err3 = self._post_json(reverse("api_insert"), {
            "title": "Yesterday",
            "artist": "The Beatles",
            "duration": 125,
            "position": 99
        })
        self.assertEqual(res_err3.status_code, 400)

        # Valid insert at position 2
        res_ok = self._post_json(reverse("api_insert"), {
            "title": "Yesterday",
            "artist": "The Beatles",
            "duration": 125,
            "position": 2
        })
        self.assertEqual(res_ok.status_code, 201)
        data = res_ok.json()
        self.assertEqual(data["total_tracks"], 6)
        self.assertEqual(data["tracks"][1]["title"], "Yesterday")
        self.assertEqual(data["tracks"][1]["position"], 2)

        # Verify DB persistence
        self.assertTrue(Track.objects.filter(title="Yesterday", position=2).exists())

    def test_delete_track_validation_and_success(self):
        """POST /api/delete/ removes track and updates subsequent positions."""
        track_to_delete = Track.objects.get(position=2)
        delete_id = track_to_delete.id

        # Missing id
        res_err1 = self._post_json(reverse("api_delete"), {})
        self.assertEqual(res_err1.status_code, 400)

        # Nonexistent id
        res_err2 = self._post_json(reverse("api_delete"), {"id": 8888})
        self.assertEqual(res_err2.status_code, 404)

        # Valid delete
        res_ok = self._post_json(reverse("api_delete"), {"id": delete_id})
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.json()["total_tracks"], 4)
        self.assertFalse(Track.objects.filter(id=delete_id).exists())

    def test_move_track_validation_and_success(self):
        """POST /api/move/ moves tracks by relinking pointers."""
        # Missing positions
        res_err1 = self._post_json(reverse("api_move"), {"pos_a": 1})
        self.assertEqual(res_err1.status_code, 400)

        # Out of bounds
        res_err2 = self._post_json(reverse("api_move"), {"pos_a": 1, "pos_b": 10})
        self.assertEqual(res_err2.status_code, 400)

        # Move track at pos 1 (Bohemian Rhapsody) to pos 3
        res_ok = self._post_json(reverse("api_move"), {"pos_a": 1, "pos_b": 3})
        self.assertEqual(res_ok.status_code, 200)
        tracks = res_ok.json()["tracks"]
        self.assertEqual(tracks[0]["title"], "Hotel California")
        self.assertEqual(tracks[1]["title"], "Billie Jean")
        self.assertEqual(tracks[2]["title"], "Bohemian Rhapsody")

        # Confirm persisted in DB
        t = Track.objects.get(title="Bohemian Rhapsody")
        self.assertEqual(t.position, 3)

    def test_persistence_across_multiple_requests(self):
        """State modifications persist cleanly across independent HTTP requests."""
        # 1. Advance track
        self.client.post(reverse("api_next"))

        # 2. In a completely separate request, verify current track
        res = self.client.get(reverse("api_state"))
        self.assertEqual(res.json()["current_track"]["title"], "Hotel California")

        # 3. Insert a song in request 3
        self._post_json(reverse("api_insert"), {
            "title": "Imagine",
            "artist": "John Lennon",
            "duration": 183
        })

        # 4. In request 4, verify total tracks is 6 and current is still Hotel California
        res4 = self.client.get(reverse("api_state"))
        self.assertEqual(res4.json()["total_tracks"], 6)
        self.assertEqual(res4.json()["current_track"]["title"], "Hotel California")

