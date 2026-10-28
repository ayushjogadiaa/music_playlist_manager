"""
Django Models for the Music Playlist Manager.

These models store persistent playlist data in SQLite:
- Track: Persists track metadata and its 1-based ordering position.
- PlaylistState: Persists the ID of the currently playing track and playback state.
"""

from django.db import models


class Track(models.Model):
    """
    Stores an individual track record in the database.

    Attributes:
        title: Title of the song.
        artist: Artist or performer name.
        duration_seconds: Song length in seconds.
        position: 1-based order index in the playlist sequence.
    """

    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255)
    duration_seconds = models.PositiveIntegerField(help_text="Duration in seconds")
    position = models.PositiveIntegerField(default=1, help_text="1-based position in playlist")

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "Track"
        verbose_name_plural = "Tracks"

    def formatted_duration(self) -> str:
        """Return duration formatted as mm:ss."""
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def to_dict(self) -> dict:
        """Return serializable dictionary of track data."""
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration_seconds,
            "formatted_duration": self.formatted_duration(),
            "position": self.position,
        }

    def __str__(self) -> str:
        return f"{self.position}. {self.title} - {self.artist} ({self.formatted_duration()})"


class PlaylistState(models.Model):
    """
    Singleton model tracking the current state of playback.

    Attributes:
        current_track_id: The ID of the currently active Track, or None.
        is_playing: Whether audio playback is currently simulating play.
    """

    current_track_id = models.IntegerField(null=True, blank=True)
    is_playing = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Playlist State"
        verbose_name_plural = "Playlist State"

    @classmethod
    def get_solo(cls) -> "PlaylistState":
        """Get or create the single state record."""
        state, _ = cls.objects.get_or_create(id=1)
        return state

    def __str__(self) -> str:
        return f"State: current_track_id={self.current_track_id}, is_playing={self.is_playing}"
