"""
Views for the Playlist Manager.

Architectural Rule:
Views remain thin. They parse and validate incoming HTTP/JSON data,
invoke the service layer, and return standard JSON responses (or render
the main HTML shell). All business and linked list logic is strictly
encapsulated in services.py and cdll.py.
"""

import json
from typing import Dict, Any
from django.shortcuts import render
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from . import services


def _parse_request_data(request: HttpRequest) -> Dict[str, Any]:
    """Helper to parse JSON payloads or form POST data cleanly."""
    if request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return request.POST.dict()


@ensure_csrf_cookie
def index(request: HttpRequest) -> HttpResponse:
    """Render the single-page application shell."""
    return render(request, "playlist/index.html")


@require_GET
def api_state(request: HttpRequest) -> JsonResponse:
    """
    GET /api/state/
    Returns the complete current playlist state.
    """
    try:
        state = services.get_state()
        return JsonResponse({"success": True, **state})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
def api_play(request: HttpRequest) -> JsonResponse:
    """
    POST /api/play/
    Body (optional): { "track_id": <int>, "is_playing": <bool> }
    Toggles playback or starts a specific track.
    """
    data = _parse_request_data(request)
    track_id = data.get("track_id")
    is_playing = data.get("is_playing")

    if track_id is not None:
        try:
            track_id = int(track_id)
        except (ValueError, TypeError):
            return JsonResponse(
                {"success": False, "error": "track_id must be an integer."},
                status=400,
            )

    if is_playing is not None and not isinstance(is_playing, bool):
        if str(is_playing).lower() in ("true", "1"):
            is_playing = True
        elif str(is_playing).lower() in ("false", "0"):
            is_playing = False
        else:
            return JsonResponse(
                {"success": False, "error": "is_playing must be a boolean."},
                status=400,
            )

    try:
        state = services.play(track_id=track_id, is_playing=is_playing)
        return JsonResponse({"success": True, **state})
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        return JsonResponse({"success": False, "error": str(e)}, status=status_code)


@require_POST
def api_next(request: HttpRequest) -> JsonResponse:
    """
    POST /api/next/
    Advances current track pointer to next node in O(1).
    """
    try:
        state = services.next_track()
        return JsonResponse({"success": True, **state})
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_POST
def api_prev(request: HttpRequest) -> JsonResponse:
    """
    POST /api/prev/
    Rewinds current track pointer to previous node in O(1).
    """
    try:
        state = services.prev_track()
        return JsonResponse({"success": True, **state})
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_POST
def api_insert(request: HttpRequest) -> JsonResponse:
    """
    POST /api/insert/
    Body: { "title": str, "artist": str, "duration": int, "position": int (optional) }
    """
    data = _parse_request_data(request)

    title = data.get("title")
    artist = data.get("artist")
    duration_raw = data.get("duration")
    position_raw = data.get("position")

    if not title or not str(title).strip():
        return JsonResponse(
            {"success": False, "error": "Title is required and cannot be blank."},
            status=400,
        )

    if not artist or not str(artist).strip():
        return JsonResponse(
            {"success": False, "error": "Artist is required and cannot be blank."},
            status=400,
        )

    if duration_raw is None or str(duration_raw).strip() == "":
        return JsonResponse(
            {"success": False, "error": "Duration in seconds is required."},
            status=400,
        )

    try:
        duration = int(duration_raw)
        if duration <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return JsonResponse(
            {"success": False, "error": "Duration must be a positive integer."},
            status=400,
        )

    position = None
    if position_raw is not None and str(position_raw).strip() != "":
        try:
            position = int(position_raw)
        except (ValueError, TypeError):
            return JsonResponse(
                {"success": False, "error": "Position must be an integer."},
                status=400,
            )

    try:
        state = services.add_track(
            title=str(title).strip(),
            artist=str(artist).strip(),
            duration=duration,
            position=position,
        )
        return JsonResponse({"success": True, **state}, status=201)
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_POST
def api_delete(request: HttpRequest) -> JsonResponse:
    """
    POST /api/delete/
    Body: { "id": int }
    """
    data = _parse_request_data(request)
    track_id_raw = data.get("id")

    if track_id_raw is None:
        return JsonResponse(
            {"success": False, "error": "Track ID 'id' is required."},
            status=400,
        )

    try:
        track_id = int(track_id_raw)
    except (ValueError, TypeError):
        return JsonResponse(
            {"success": False, "error": "Track ID must be an integer."},
            status=400,
        )

    try:
        state = services.delete_track(track_id)
        return JsonResponse({"success": True, **state})
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400
        return JsonResponse({"success": False, "error": str(e)}, status=status_code)


@require_POST
def api_move(request: HttpRequest) -> JsonResponse:
    """
    POST /api/move/
    Body: { "pos_a": int, "pos_b": int }
    """
    data = _parse_request_data(request)
    pos_a_raw = data.get("pos_a")
    pos_b_raw = data.get("pos_b")

    if pos_a_raw is None or pos_b_raw is None:
        return JsonResponse(
            {"success": False, "error": "Both 'pos_a' and 'pos_b' are required."},
            status=400,
        )

    try:
        pos_a = int(pos_a_raw)
        pos_b = int(pos_b_raw)
    except (ValueError, TypeError):
        return JsonResponse(
            {"success": False, "error": "Positions must be valid integers."},
            status=400,
        )

    try:
        state = services.move_track(pos_a, pos_b)
        return JsonResponse({"success": True, **state})
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
