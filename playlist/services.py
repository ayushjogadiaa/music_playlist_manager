"""
Service layer bridging Django's SQLite persistence with the Circular Doubly Linked List.

ARCHITECTURE:
Django creates fresh objects on every HTTP request and discards them after
sending the response. Memory is not shared across requests.

To maintain algorithmic purity and satisfy DSA requirements:
1. All playlist operations (insert, delete, move, navigate) are performed
   PURELY ON THE IN-MEMORY CDLL via pointers.
2. For each request:
   a. Load Track records from the DB ordered by position.
   b. Reconstruct the CircularDoublyLinkedList in memory.
   c. Execute the CDLL pointer operation.
   d. Write the updated track positions and current_track_id back to SQLite.
"""

from typing import Optional, Dict, Any, List
from django.db import transaction
from .models import Track, PlaylistState
from .cdll import Node, CircularDoublyLinkedList


SAMPLE_TRACKS = [
    {"title": "Bohemian Rhapsody", "artist": "Queen", "duration_seconds": 354},
    {"title": "Hotel California", "artist": "Eagles", "duration_seconds": 391},
    {"title": "Billie Jean", "artist": "Michael Jackson", "duration_seconds": 294},
    {"title": "Shape of You", "artist": "Ed Sheeran", "duration_seconds": 233},
    {"title": "Blinding Lights", "artist": "The Weeknd", "duration_seconds": 200},
]


def seed_sample_tracks() -> None:
    """
    Populate the database with 5 initial sample songs if the DB is empty.
    Sets the first track as the current active track.
    """
    if Track.objects.exists():
        return

    with transaction.atomic():
        created_tracks = []
        for index, item in enumerate(SAMPLE_TRACKS, start=1):
            track = Track.objects.create(
                title=item["title"],
                artist=item["artist"],
                duration_seconds=item["duration_seconds"],
                position=index,
            )
            created_tracks.append(track)

        state = PlaylistState.get_solo()
        if created_tracks:
            state.current_track_id = created_tracks[0].id
            state.is_playing = False
            state.save()


def _load_cdll_from_db() -> CircularDoublyLinkedList:
    """
    Load all tracks from SQLite ordered by position and construct a CDLL.
    Restores the 'current' pointer using PlaylistState.

    Time Complexity: O(n) to query DB and build the CDLL of n nodes.
    """
    cdll = CircularDoublyLinkedList()
    tracks = list(Track.objects.all().order_by("position", "id"))

    if not tracks:
        return cdll

    for t in tracks:
        node = Node(
            id=t.id,
            title=t.title,
            artist=t.artist,
            duration=t.duration_seconds,
        )
        cdll.insert_at_end(node)

    state = PlaylistState.get_solo()
    if state.current_track_id:
        found = cdll.set_current_by_id(state.current_track_id)
        if not found:
            cdll.current = cdll.head
    else:
        cdll.current = cdll.head

    return cdll


def _save_cdll_to_db(cdll: CircularDoublyLinkedList, is_playing: Optional[bool] = None) -> None:
    """
    Write the CDLL's current sequence and playback pointer back to SQLite.

    Time Complexity: O(n) to iterate the list and update positions in DB.
    """
    ordered_nodes = cdll.to_list()

    with transaction.atomic():
        # Update 1-based position for each node
        for pos, node in enumerate(ordered_nodes, start=1):
            Track.objects.filter(id=node.id).update(position=pos)

        state = PlaylistState.get_solo()
        state.current_track_id = cdll.current.id if cdll.current else None
        if is_playing is not None:
            state.is_playing = is_playing
        state.save()


def get_state() -> Dict[str, Any]:
    """
    Retrieve current playlist state for views and API responses.
    Auto-seeds sample tracks if the database is completely empty.

    Returns:
        dict containing:
        - current_track: Dict with metadata or None
        - previous_track: Dict with metadata or None
        - upcoming_tracks: List of up to 3 upcoming track dicts
        - tracks: Full ordered list of tracks with position and is_current flag
        - total_tracks: Total track count
        - is_playing: Current playback state
    """
    if not Track.objects.exists():
        seed_sample_tracks()

    cdll = _load_cdll_from_db()
    state = PlaylistState.get_solo()

    curr = cdll.get_current()
    prev = cdll.get_previous()
    upcoming = cdll.get_upcoming(3)
    all_nodes = cdll.to_list()

    tracks_payload = []
    for idx, node in enumerate(all_nodes, start=1):
        item = node.to_dict()
        item["position"] = idx
        item["is_current"] = (curr is not None and node.id == curr.id)
        tracks_payload.append(item)

    return {
        "current_track": curr.to_dict() if curr else None,
        "previous_track": prev.to_dict() if prev else None,
        "upcoming_tracks": [n.to_dict() for n in upcoming],
        "tracks": tracks_payload,
        "total_tracks": len(cdll),
        "is_playing": state.is_playing,
    }


def play(track_id: Optional[int] = None, is_playing: Optional[bool] = None) -> Dict[str, Any]:
    """
    Start, pause, or switch playback to a specific track.
    """
    cdll = _load_cdll_from_db()
    state = PlaylistState.get_solo()

    if track_id is not None:
        if not cdll.set_current_by_id(track_id):
            raise ValueError(f"Track ID {track_id} not found in playlist.")
        new_is_playing = True if is_playing is None else is_playing
    else:
        if is_playing is not None:
            new_is_playing = is_playing
        else:
            new_is_playing = not state.is_playing

    _save_cdll_to_db(cdll, is_playing=new_is_playing)
    return get_state()


def next_track() -> Dict[str, Any]:
    """
    Advance to the next track using CDLL O(1) circular pointer navigation.
    """
    cdll = _load_cdll_from_db()
    if cdll.is_empty():
        raise ValueError("Playlist is empty.")

    cdll.next_track()
    _save_cdll_to_db(cdll)
    return get_state()


def prev_track() -> Dict[str, Any]:
    """
    Rewind to the previous track using CDLL O(1) circular pointer navigation.
    """
    cdll = _load_cdll_from_db()
    if cdll.is_empty():
        raise ValueError("Playlist is empty.")

    cdll.prev_track()
    _save_cdll_to_db(cdll)
    return get_state()


def add_track(
    title: str, artist: str, duration: int, position: Optional[int] = None
) -> Dict[str, Any]:
    """
    Add a track to the playlist at a specific 1-based position or at the end.
    All position adjustments and pointer linking happen on the CDLL.
    """
    if not title or not title.strip():
        raise ValueError("Song title cannot be empty.")
    if not artist or not artist.strip():
        raise ValueError("Artist cannot be empty.")
    if duration <= 0:
        raise ValueError("Duration must be a positive number of seconds.")

    cdll = _load_cdll_from_db()

    target_pos = position if position is not None else (cdll.size + 1)
    if target_pos < 1 or target_pos > cdll.size + 1:
        raise ValueError(
            f"Position {target_pos} is out of range. Valid range: 1 to {cdll.size + 1}."
        )

    # Create the persistent record in SQLite
    track = Track.objects.create(
        title=title.strip(),
        artist=artist.strip(),
        duration_seconds=duration,
        position=target_pos,
    )

    # Construct the Node and link it into the CDLL
    new_node = Node(
        id=track.id,
        title=track.title,
        artist=track.artist,
        duration=track.duration_seconds,
    )

    cdll.insert_at_position(target_pos, new_node)
    _save_cdll_to_db(cdll)
    return get_state()


def delete_track(track_id: int) -> Dict[str, Any]:
    """
    Remove a track by its ID from the playlist.
    Unlinks the node in the CDLL and removes its row from SQLite.
    """
    cdll = _load_cdll_from_db()
    if cdll.is_empty():
        raise ValueError("Cannot delete from an empty playlist.")

    cdll.delete_by_id(track_id)
    Track.objects.filter(id=track_id).delete()

    _save_cdll_to_db(cdll)
    return get_state()


def move_track(pos_a: int, pos_b: int) -> Dict[str, Any]:
    """
    Move a track from pos_a to pos_b by unlinking and relinking in the CDLL.
    """
    cdll = _load_cdll_from_db()
    if cdll.is_empty():
        raise ValueError("Playlist is empty.")

    cdll.move(pos_a, pos_b)
    _save_cdll_to_db(cdll)
    return get_state()

