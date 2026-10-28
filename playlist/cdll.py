"""
Circular Doubly Linked List (CDLL) Data Structure for Music Playlist Manager.

This module is completely independent of Django and implements a manual
Circular Doubly Linked List with Node objects and next/prev pointers.
No external packages or Python collection classes (list/deque) are used
internally to maintain list state.
"""

from typing import Optional, List, Dict, Any


class Node:
    """
    Represents a single track node in a Circular Doubly Linked List (CDLL).

    Attributes:
        id: Unique identifier for the track (matches DB Track.id).
        title: Title of the song.
        artist: Artist or performer name.
        duration: Duration of the song in seconds (integer).
        next: Pointer to the next Node in the ring.
        prev: Pointer to the previous Node in the ring.
    """

    def __init__(
        self,
        id: int,
        title: str,
        artist: str,
        duration: int,
        next_node: Optional["Node"] = None,
        prev_node: Optional["Node"] = None,
    ) -> None:
        """
        Initialize a new track Node.

        In a circular doubly linked list, a standalone node starts as a
        'ring of one'. Its next pointer points to itself, and its prev
        pointer also points to itself.

        Time Complexity: O(1)
        """
        self.id = id
        self.title = title
        self.artist = artist
        self.duration = int(duration)

        # POINTER OPERATION:
        # If explicit neighbors are not provided, close the ring on itself.
        # [self] <---> [self] (next points to self, prev points to self)
        self.next: "Node" = next_node if next_node is not None else self
        self.prev: "Node" = prev_node if prev_node is not None else self

    def formatted_duration(self) -> str:
        """
        Format the duration in seconds to a human-readable mm:ss string.

        Example:
            195 seconds -> "03:15"

        Time Complexity: O(1)
        """
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a dictionary representation of the track metadata.
        Does not serialize pointer references to prevent circular recursion.

        Time Complexity: O(1)
        """
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration,
            "formatted_duration": self.formatted_duration(),
        }

    def __repr__(self) -> str:
        """
        String representation for debugging and console display.

        Time Complexity: O(1)
        """
        return f"Node(id={self.id}, title='{self.title}', artist='{self.artist}', duration={self.formatted_duration()})"


class CircularDoublyLinkedList:
    """
    Manual implementation of a Circular Doubly Linked List (CDLL).

    In this data structure:
    - Each node has a pointer to the next node and the previous node.
    - The last node's 'next' points back to 'head'.
    - The 'head' node's 'prev' points to the last node (tail).
    - 'current' tracks the currently playing node.
    - No node ever has next is None or prev is None (unless the list is empty).

    Attributes:
        head: Pointer to the first track in the playlist.
        current: Pointer to the currently active/playing track.
        size: Number of tracks in the playlist.
    """

    def __init__(self) -> None:
        """
        Initialize an empty Circular Doubly Linked List.

        Time Complexity: O(1)
        """
        self.head: Optional[Node] = None
        self.current: Optional[Node] = None
        self.size: int = 0

    def is_empty(self) -> bool:
        """
        Check if the playlist contains zero tracks.

        Time Complexity: O(1)
        """
        return self.size == 0

    def __len__(self) -> int:
        """
        Return the total number of tracks in the playlist.

        Time Complexity: O(1)
        """
        return self.size

    def insert_at_end(self, node: Node) -> None:
        """
        Insert a new node at the end of the circular playlist.

        Because this is a CDLL, the tail of the list is always accessed
        in O(1) time via self.head.prev!

        Time Complexity: O(1)
        """
        if self.is_empty():
            # LIST WAS EMPTY:
            # The new node becomes both head and current.
            # It forms a self-contained ring of 1.
            self.head = node
            self.current = node
            node.next = node
            node.prev = node
            self.size = 1
            return

        # LIST HAS AT LEAST 1 NODE:
        # In CDLL, tail is immediately accessible:
        tail = self.head.prev

        # POINTER OPERATIONS to insert 'node' between 'tail' and 'head':
        # 1. Connect tail's next to the new node
        tail.next = node
        # 2. Connect new node's prev to tail
        node.prev = tail
        # 3. Connect new node's next to head
        node.next = self.head
        # 4. Connect head's prev to new node (new tail)
        self.head.prev = node

        # If current was somehow None, point it to head
        if self.current is None:
            self.current = self.head

        self.size += 1

    def insert_at_position(self, pos: int, node: Node) -> None:
        """
        Insert a new node at a 1-based position in the playlist.

        Valid range: 1 <= pos <= size + 1
        - pos == 1: New head of the playlist.
        - pos == size + 1: Append at the end.
        - 2 <= pos <= size: Insert before the node currently at pos.

        Time Complexity: O(n) to locate the target position, O(1) to relink.
        """
        if pos < 1 or pos > self.size + 1:
            raise ValueError(
                f"Position {pos} is out of range. Valid range is 1 to {self.size + 1}."
            )

        # Case 1: Empty list (pos must be 1)
        if self.is_empty():
            self.insert_at_end(node)
            return

        # Case 2: Append at end
        if pos == self.size + 1:
            self.insert_at_end(node)
            return

        # Case 3: Insert at position 1 (new head)
        if pos == 1:
            tail = self.head.prev

            # POINTER OPERATIONS to place node before current head:
            node.next = self.head
            node.prev = tail
            tail.next = node
            self.head.prev = node

            # Advance head pointer to the new node
            self.head = node
            self.size += 1
            return

        # Case 4: Insert in the middle (2 <= pos <= size)
        # Walk to the node currently occupying 'pos' (target)
        curr = self.head
        for _ in range(pos - 1):
            curr = curr.next

        # We will insert 'node' right before 'curr' (between curr.prev and curr)
        prev_node = curr.prev

        # POINTER OPERATIONS:
        # [prev_node] <---> [node] <---> [curr]
        prev_node.next = node
        node.prev = prev_node
        node.next = curr
        curr.prev = node

        self.size += 1

    def next_track(self) -> Optional[Node]:
        """
        Advance playback to the next track in the ring.

        Because the CDLL is circular, advancing past the tail seamlessly
        lands right back at the head without any index bounds check.

        Time Complexity: O(1)
        """
        if self.is_empty() or self.current is None:
            return None

        # POINTER OPERATION: Step forward structurally in O(1)
        self.current = self.current.next
        return self.current

    def prev_track(self) -> Optional[Node]:
        """
        Step playback backward to the previous track in the ring.

        Because the CDLL is circular, reversing past the head seamlessly
        lands at the tail without any index bounds check.

        Time Complexity: O(1)
        """
        if self.is_empty() or self.current is None:
            return None

        # POINTER OPERATION: Step backward structurally in O(1)
        self.current = self.current.prev
        return self.current

    def set_current_by_id(self, track_id: int) -> bool:
        """
        Find a track by ID and set it as the currently playing track.

        Time Complexity: O(n)
        """
        if self.is_empty():
            return False

        curr = self.head
        for _ in range(self.size):
            if curr.id == track_id:
                self.current = curr
                return True
            curr = curr.next

        return False

    def delete_by_id(self, track_id: int) -> Node:
        """
        Remove the track with the given ID from the playlist.

        Edge cases handled:
        - Empty list: raises ValueError.
        - Single-node list: head and current both become None.
        - Deleting head: head moves to head.next.
        - Deleting current: current moves to the next track.
        - ID not found: raises ValueError.

        Time Complexity: O(n) to locate the node, O(1) to relink pointers.
        """
        if self.is_empty():
            raise ValueError("Cannot delete from an empty playlist.")

        # Find the target node
        target: Optional[Node] = None
        curr = self.head
        for _ in range(self.size):
            if curr.id == track_id:
                target = curr
                break
            curr = curr.next

        if target is None:
            raise ValueError(f"Track with ID {track_id} not found in playlist.")

        # Edge case: Exactly 1 node in the playlist
        if self.size == 1:
            self.head = None
            self.current = None
            self.size = 0
            # Isolate deleted node
            target.next = target
            target.prev = target
            return target

        # Edge case: More than 1 node
        is_deleting_head = (target is self.head)
        is_deleting_current = (target is self.current)

        # POINTER OPERATIONS to bridge over 'target':
        # A <---> [target] <---> C
        # becomes A <---> C
        prev_node = target.prev
        next_node = target.next

        prev_node.next = next_node
        next_node.prev = prev_node

        # Update head if target was the head
        if is_deleting_head:
            self.head = next_node

        # Update current if target was the current playing track
        if is_deleting_current:
            self.current = next_node

        self.size -= 1

        # Isolate the removed node's pointers for safety
        target.next = target
        target.prev = target
        return target

    def move(self, pos_a: int, pos_b: int) -> None:
        """
        Move a track from 1-based position pos_a to 1-based position pos_b.

        Does NOT create a new node. Only unlinks the existing node at pos_a
        and relinks it at pos_b, preserving id, metadata, and identity.
        If the moved track is the current track, it remains the current track.

        Time Complexity: O(n) to locate positions, O(1) to relink pointers.
        """
        if pos_a < 1 or pos_a > self.size:
            raise ValueError(
                f"Source position {pos_a} out of range (1 to {self.size})."
            )
        if pos_b < 1 or pos_b > self.size:
            raise ValueError(
                f"Destination position {pos_b} out of range (1 to {self.size})."
            )

        # No-op if source and destination are identical
        if pos_a == pos_b:
            return

        # STEP 1: Locate node at pos_a
        node_a = self.head
        for _ in range(pos_a - 1):
            node_a = node_a.next

        # STEP 2: Unlink node_a from its current neighbors
        # A <---> [node_a] <---> C  ==>  A <---> C
        prev_a = node_a.prev
        next_a = node_a.next

        prev_a.next = next_a
        next_a.prev = prev_a

        # If node_a was head, temporarily designate next_a as head
        if self.head is node_a:
            self.head = next_a

        self.size -= 1

        # STEP 3: Relink node_a at pos_b in the remaining list of size (n - 1)
        # Note: pos_b is in range 1 .. old_size, which equals 1 .. (new_size + 1)
        if pos_b == 1:
            # Insert as new head
            tail = self.head.prev
            node_a.next = self.head
            node_a.prev = tail
            tail.next = node_a
            self.head.prev = node_a
            self.head = node_a
            self.size += 1
            return

        if pos_b == self.size + 1:
            # Append at end (becomes new tail)
            tail = self.head.prev
            tail.next = node_a
            node_a.prev = tail
            node_a.next = self.head
            self.head.prev = node_a
            self.size += 1
            return

        # Insert before the node currently at pos_b in the remaining list
        target = self.head
        for _ in range(pos_b - 1):
            target = target.next

        # Insert node_a immediately before target
        prev_target = target.prev
        prev_target.next = node_a
        node_a.prev = prev_target
        node_a.next = target
        target.prev = node_a

        self.size += 1

    def get_current(self) -> Optional[Node]:
        """
        Return the currently playing track node, or None if playlist is empty.

        Time Complexity: O(1)
        """
        return self.current

    def get_previous(self) -> Optional[Node]:
        """
        Return the track immediately before the current track in the ring.

        Time Complexity: O(1)
        """
        if self.is_empty() or self.current is None:
            return None
        return self.current.prev

    def get_upcoming(self, k: int = 3) -> List[Node]:
        """
        Return up to k upcoming tracks walking forward from current.

        Prevents repetition: if k >= size, stops early so no track is
        repeated in the upcoming list.

        Time Complexity: O(min(k, n))
        """
        if self.is_empty() or self.current is None or self.size <= 1:
            return []

        # At most (size - 1) upcoming tracks without repeating current
        count = min(k, self.size - 1)
        upcoming: List[Node] = []
        curr = self.current.next

        for _ in range(count):
            upcoming.append(curr)
            curr = curr.next

        return upcoming

    def to_list(self) -> List[Node]:
        """
        Return a plain Python list of all track nodes ordered from head to tail.

        Uses a do-while style loop because in a CDLL there is no 'None' sentinel
        to mark the end; we stop when curr wraps back to self.head.

        Time Complexity: O(n)
        """
        if self.is_empty() or self.head is None:
            return []

        result: List[Node] = []
        curr = self.head
        while True:
            result.append(curr)
            curr = curr.next
            # STRUCTURAL TERMINATION: Stopped when we complete one full circle
            if curr is self.head:
                break

        return result

    def verify_integrity(self) -> bool:
        """
        Verify the mathematical invariants of the Circular Doubly Linked List:
        1. If empty: head and current are None, size is 0.
        2. If non-empty:
           - Walking 'next' exactly 'size' times returns to 'head'.
           - Walking 'prev' exactly 'size' times returns to 'head'.
           - Every node satisfies: node.next.prev == node.
           - Every node satisfies: node.prev.next == node.
           - 'current' is a valid node reachable in the ring.

        Raises AssertionError if any invariant is violated.
        Returns True when all invariants hold.

        Time Complexity: O(n)
        """
        if self.size == 0:
            assert self.head is None, "Empty list must have head is None"
            assert self.current is None, "Empty list must have current is None"
            return True

        assert self.head is not None, "Non-empty list must have head"
        assert self.current is not None, "Non-empty list must have current"

        # FORWARD INTEGRITY CHECK
        curr = self.head
        current_found = False

        for step in range(self.size):
            if curr is self.current:
                current_found = True

            # Invariant: Two-way linkage
            assert (
                curr.next.prev is curr
            ), f"Invariant broken at step {step}: curr.next.prev is not curr"
            assert (
                curr.prev.next is curr
            ), f"Invariant broken at step {step}: curr.prev.next is not curr"

            curr = curr.next

        assert (
            curr is self.head
        ), f"Forward traversal failed to return to head after {self.size} steps"
        assert current_found, "Current node is not present in the playlist ring"

        # BACKWARD INTEGRITY CHECK
        curr = self.head
        for _ in range(self.size):
            curr = curr.prev

        assert (
            curr is self.head
        ), f"Backward traversal failed to return to head after {self.size} steps"

        return True
