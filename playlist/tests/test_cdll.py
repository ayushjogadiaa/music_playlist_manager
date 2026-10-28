"""
Pure Python Unit Tests for Circular Doubly Linked List (CDLL).

This test suite has ZERO dependencies on Django.
It verifies all pointer operations, wrap-around navigation, insertions,
deletions, moves, and edge cases, running verify_integrity() after
every single mutation.
"""

import unittest
from playlist.cdll import Node, CircularDoublyLinkedList


class TestCircularDoublyLinkedList(unittest.TestCase):
    """Test suite for CDLL structure, invariants, and edge cases."""

    def setUp(self):
        """Create a fresh list before each test."""
        self.cdll = CircularDoublyLinkedList()

    def _create_node(self, track_id: int, title: str = "Song", duration: int = 180) -> Node:
        return Node(
            id=track_id,
            title=f"{title} {track_id}",
            artist=f"Artist {track_id}",
            duration=duration,
        )

    def test_node_initialization(self):
        """A standalone node forms a self-contained ring of 1."""
        node = self._create_node(1, "Stand By Me", 182)
        self.assertEqual(node.id, 1)
        self.assertEqual(node.formatted_duration(), "03:02")
        self.assertIs(node.next, node)
        self.assertIs(node.prev, node)

    def test_empty_list(self):
        """Test properties of an empty list."""
        self.assertTrue(self.cdll.is_empty())
        self.assertEqual(len(self.cdll), 0)
        self.assertIsNone(self.cdll.get_current())
        self.assertIsNone(self.cdll.get_previous())
        self.assertEqual(self.cdll.get_upcoming(3), [])
        self.assertEqual(self.cdll.to_list(), [])
        self.assertTrue(self.cdll.verify_integrity())
        self.assertIsNone(self.cdll.next_track())
        self.assertIsNone(self.cdll.prev_track())

    def test_insert_at_end_single_node(self):
        """Insert one node and verify pointers and current track."""
        n1 = self._create_node(1)
        self.cdll.insert_at_end(n1)
        self.cdll.verify_integrity()

        self.assertFalse(self.cdll.is_empty())
        self.assertEqual(len(self.cdll), 1)
        self.assertIs(self.cdll.head, n1)
        self.assertIs(self.cdll.current, n1)
        self.assertIs(n1.next, n1)
        self.assertIs(n1.prev, n1)

    def test_insert_at_end_multiple_nodes(self):
        """Insert 3 nodes at end and verify tail-head connection."""
        n1 = self._create_node(1)
        n2 = self._create_node(2)
        n3 = self._create_node(3)

        self.cdll.insert_at_end(n1)
        self.cdll.verify_integrity()
        self.cdll.insert_at_end(n2)
        self.cdll.verify_integrity()
        self.cdll.insert_at_end(n3)
        self.cdll.verify_integrity()

        self.assertEqual(len(self.cdll), 3)
        self.assertIs(self.cdll.head, n1)
        # Verify circular linkage: n3 is tail, n3.next is n1, n1.prev is n3
        self.assertIs(self.cdll.head.prev, n3)
        self.assertIs(n3.next, n1)
        self.assertIs(n1.next, n2)
        self.assertIs(n2.next, n3)
        self.assertIs(n3.prev, n2)
        self.assertIs(n2.prev, n1)

        ids = [n.id for n in self.cdll.to_list()]
        self.assertEqual(ids, [1, 2, 3])

    def test_insert_at_position_head_middle_end(self):
        """Test inserting at pos=1 (new head), middle, and pos=size+1 (tail)."""
        # 1. Insert into empty list at pos 1
        n2 = self._create_node(2)
        self.cdll.insert_at_position(1, n2)
        self.cdll.verify_integrity()
        self.assertEqual([n.id for n in self.cdll.to_list()], [2])

        # 2. Insert at pos 1 (new head)
        n1 = self._create_node(1)
        self.cdll.insert_at_position(1, n1)
        self.cdll.verify_integrity()
        self.assertIs(self.cdll.head, n1)
        self.assertEqual([n.id for n in self.cdll.to_list()], [1, 2])

        # 3. Insert at pos 3 (end / pos == size + 1)
        n4 = self._create_node(4)
        self.cdll.insert_at_position(3, n4)
        self.cdll.verify_integrity()
        self.assertEqual([n.id for n in self.cdll.to_list()], [1, 2, 4])

        # 4. Insert at middle (pos 3, between 2 and 4)
        n3 = self._create_node(3)
        self.cdll.insert_at_position(3, n3)
        self.cdll.verify_integrity()
        self.assertEqual([n.id for n in self.cdll.to_list()], [1, 2, 3, 4])

    def test_insert_invalid_position(self):
        """Attempting to insert out of range raises ValueError."""
        n1 = self._create_node(1)
        self.cdll.insert_at_end(n1)

        with self.assertRaises(ValueError):
            self.cdll.insert_at_position(0, self._create_node(99))

        with self.assertRaises(ValueError):
            self.cdll.insert_at_position(3, self._create_node(99))

    def test_navigation_and_wraparound(self):
        """Test next_track and prev_track with circular wrap-around."""
        n1 = self._create_node(1)
        n2 = self._create_node(2)
        n3 = self._create_node(3)
        for n in (n1, n2, n3):
            self.cdll.insert_at_end(n)

        # Initial current is n1
        self.assertIs(self.cdll.get_current(), n1)

        # Next: n1 -> n2 -> n3 -> n1 (wrap-around!)
        self.assertIs(self.cdll.next_track(), n2)
        self.assertIs(self.cdll.next_track(), n3)
        self.assertIs(self.cdll.next_track(), n1)  # Wrapped to head!

        # Prev: n1 -> n3 -> n2 -> n1 (wrap-around reverse!)
        self.assertIs(self.cdll.prev_track(), n3)  # Wrapped to tail!
        self.assertIs(self.cdll.prev_track(), n2)
        self.assertIs(self.cdll.prev_track(), n1)

    def test_single_node_navigation(self):
        """Single node playlist next and prev return that same node."""
        n1 = self._create_node(1)
        self.cdll.insert_at_end(n1)

        self.assertIs(self.cdll.next_track(), n1)
        self.assertIs(self.cdll.prev_track(), n1)

    def test_delete_only_node(self):
        """Deleting the single track in a playlist leaves an empty list."""
        n1 = self._create_node(1)
        self.cdll.insert_at_end(n1)

        deleted = self.cdll.delete_by_id(1)
        self.cdll.verify_integrity()
        self.assertIs(deleted, n1)
        self.assertTrue(self.cdll.is_empty())
        self.assertIsNone(self.cdll.head)
        self.assertIsNone(self.cdll.current)

    def test_delete_head(self):
        """Deleting the head shifts head to head.next."""
        n1 = self._create_node(1)
        n2 = self._create_node(2)
        n3 = self._create_node(3)
        for n in (n1, n2, n3):
            self.cdll.insert_at_end(n)

        deleted = self.cdll.delete_by_id(1)
        self.cdll.verify_integrity()
        self.assertIs(deleted, n1)
        self.assertIs(self.cdll.head, n2)
        self.assertEqual([n.id for n in self.cdll.to_list()], [2, 3])

    def test_delete_tail(self):
        """Deleting the tail connects head.prev to the second-to-last node."""
        n1 = self._create_node(1)
        n2 = self._create_node(2)
        n3 = self._create_node(3)
        for n in (n1, n2, n3):
            self.cdll.insert_at_end(n)

        deleted = self.cdll.delete_by_id(3)
        self.cdll.verify_integrity()
        self.assertIs(deleted, n3)
        self.assertIs(self.cdll.head.prev, n2)
        self.assertIs(n2.next, n1)
        self.assertEqual([n.id for n in self.cdll.to_list()], [1, 2])

    def test_delete_middle(self):
        """Deleting a middle node bridges prev and next."""
        n1 = self._create_node(1)
        n2 = self._create_node(2)
        n3 = self._create_node(3)
        for n in (n1, n2, n3):
            self.cdll.insert_at_end(n)

        deleted = self.cdll.delete_by_id(2)
        self.cdll.verify_integrity()
        self.assertIs(deleted, n2)
        self.assertEqual([n.id for n in self.cdll.to_list()], [1, 3])
        self.assertIs(n1.next, n3)
        self.assertIs(n3.prev, n1)

    def test_delete_current_track(self):
        """Deleting the currently playing track shifts current to the next track."""
        n1 = self._create_node(1)
        n2 = self._create_node(2)
        n3 = self._create_node(3)
        for n in (n1, n2, n3):
            self.cdll.insert_at_end(n)

        self.cdll.set_current_by_id(2)
        self.assertIs(self.cdll.current, n2)

        self.cdll.delete_by_id(2)
        self.cdll.verify_integrity()
        # Current must advance to n3
        self.assertIs(self.cdll.current, n3)

    def test_delete_nonexistent_or_empty(self):
        """Deleting from empty list or with invalid id raises ValueError."""
        with self.assertRaises(ValueError):
            self.cdll.delete_by_id(1)

        self.cdll.insert_at_end(self._create_node(1))
        with self.assertRaises(ValueError):
            self.cdll.delete_by_id(999)

    def test_move_forward(self):
        """Move track from position 1 to position 3."""
        nodes = [self._create_node(i) for i in range(1, 5)]
        for n in nodes:
            self.cdll.insert_at_end(n)

        # Initial: [1, 2, 3, 4]
        self.cdll.move(1, 3)
        self.cdll.verify_integrity()
        # Node 1 moved to position 3 -> [2, 3, 1, 4]
        self.assertEqual([n.id for n in self.cdll.to_list()], [2, 3, 1, 4])
        self.assertIs(self.cdll.head, nodes[1])  # node 2 is new head

    def test_move_backward(self):
        """Move track from position 4 to position 2."""
        nodes = [self._create_node(i) for i in range(1, 5)]
        for n in nodes:
            self.cdll.insert_at_end(n)

        # Initial: [1, 2, 3, 4]
        self.cdll.move(4, 2)
        self.cdll.verify_integrity()
        # Node 4 moved to pos 2 -> [1, 4, 2, 3]
        self.assertEqual([n.id for n in self.cdll.to_list()], [1, 4, 2, 3])

    def test_move_to_end(self):
        """Move position 2 to position 4 (end)."""
        nodes = [self._create_node(i) for i in range(1, 5)]
        for n in nodes:
            self.cdll.insert_at_end(n)

        self.cdll.move(2, 4)
        self.cdll.verify_integrity()
        self.assertEqual([n.id for n in self.cdll.to_list()], [1, 3, 4, 2])

    def test_move_to_start(self):
        """Move position 3 to position 1 (new head)."""
        nodes = [self._create_node(i) for i in range(1, 5)]
        for n in nodes:
            self.cdll.insert_at_end(n)

        self.cdll.move(3, 1)
        self.cdll.verify_integrity()
        self.assertEqual([n.id for n in self.cdll.to_list()], [3, 1, 2, 4])
        self.assertIs(self.cdll.head, nodes[2])

    def test_move_same_position(self):
        """Moving to same position is a safe no-op."""
        nodes = [self._create_node(i) for i in range(1, 4)]
        for n in nodes:
            self.cdll.insert_at_end(n)

        self.cdll.move(2, 2)
        self.cdll.verify_integrity()
        self.assertEqual([n.id for n in self.cdll.to_list()], [1, 2, 3])

    def test_move_preserves_current_track(self):
        """Moving the currently playing track keeps that exact node as current."""
        nodes = [self._create_node(i) for i in range(1, 5)]
        for n in nodes:
            self.cdll.insert_at_end(n)

        self.cdll.set_current_by_id(2)
        self.assertIs(self.cdll.current, nodes[1])

        # Move node 2 from pos 2 to pos 4
        self.cdll.move(2, 4)
        self.cdll.verify_integrity()
        self.assertIs(self.cdll.current, nodes[1])  # Still node 2!

    def test_move_invalid_positions(self):
        """Out of range pos_a or pos_b raises ValueError."""
        nodes = [self._create_node(i) for i in range(1, 4)]
        for n in nodes:
            self.cdll.insert_at_end(n)

        with self.assertRaises(ValueError):
            self.cdll.move(0, 2)
        with self.assertRaises(ValueError):
            self.cdll.move(1, 4)
        with self.assertRaises(ValueError):
            self.cdll.move(4, 1)

    def test_display_helpers_and_upcoming(self):
        """Test get_previous, get_upcoming with k >= size, and to_list."""
        nodes = [self._create_node(i) for i in range(1, 6)]
        for n in nodes:
            self.cdll.insert_at_end(n)

        self.cdll.set_current_by_id(3)
        self.assertEqual(self.cdll.get_previous().id, 2)

        # In a list of 5 songs, current is 3:
        # upcoming 3 tracks: 4, 5, 1 (wraps to 1)
        upcoming = self.cdll.get_upcoming(3)
        self.assertEqual([n.id for n in upcoming], [4, 5, 1])

        # Upcoming with k=10: should stop at size - 1 = 4 to avoid repeating current
        upcoming_large = self.cdll.get_upcoming(10)
        self.assertEqual([n.id for n in upcoming_large], [4, 5, 1, 2])


if __name__ == "__main__":
    unittest.main()

