# 🎵 Music Playlist Manager (Circular Doubly Linked List)

A second-year Data Structures and Algorithms (DSA) microproject demonstrating a **Music Playlist Manager** powered by a **Circular Doubly Linked List (CDLL)**.

Built with **Python 3.11+**, **Django 5.x / 6.x**, **SQLite**, and vanilla **HTML/CSS/JavaScript**.

---

## 📌 Project Overview

In music player applications (like Spotify or Apple Music), playlists support:
1. **Continuous Looping:** When the last song finishes, playback seamlessly wraps around to the first song without special bounds checking.
2. **Bidirectional Navigation:** Moving forward (`next`) and backward (`prev`) are instant $O(1)$ pointer dereferences.
3. **Arbitrary Reordering & Deletion:** Tracks can be moved or deleted without shifting contiguous memory arrays.

A **Circular Doubly Linked List (CDLL)** is the ideal theoretical data structure for this behavior. This project implements the CDLL manually from scratch (using custom `Node` objects and pointer references, with zero list/collection dependencies inside the data structure) and provides an interactive web UI with real-time ring visualization and an interactive DSA command console.

---

## 🏛️ Architecture & Web Setting Trade-Off

### Stateless HTTP vs. In-Memory Pointers

In desktop applications, data structures live in continuous RAM. However, **Django and standard web frameworks are stateless**:
- Each HTTP request is handled in isolation by a new process or thread.
- Python memory objects are destroyed once an HTTP response is returned.

To maintain algorithmic integrity while serving web requests, this project uses a 4-tier architecture:

```
[Browser UI / Vanilla JS]
        │  HTTP / JSON (REST API)
        ▼
[Thin Views (views.py)]
        │  Parses inputs, validates parameters
        ▼
[Service Layer (services.py)]  <───> [SQLite Database (models.py)]
  1. Load tracks from DB (O(n))        • Track (id, title, artist, duration, position)
  2. Build in-memory CDLL (O(n))       • PlaylistState (current_track_id, is_playing)
  3. Execute operation ON CDLL (O(1) / O(n))
  4. Write updated order & state back to DB (O(n))
        ▼
[CDLL Data Structure (cdll.py)]
  • Pure Python, 0 Django dependencies
  • Manual Node pointer relinking (next, prev)
```

> **Honest Complexity Trade-off:**
> In pure RAM, pointer operations like `next_track()` and `prev_track()` are $O(1)$. However, because Django reconstructs the CDLL from the SQLite database on each HTTP request and flushes updated positions back on mutation, the web bridge incurs an $O(n)$ database retrieval and serialization cost per request. This is a deliberate, well-understood trade-off between web persistence and pure data structure manipulation.

---

## 🪢 Circular Doubly Linked List (CDLL) Pointer Diagram

In a CDLL, every node maintains two pointers: `next` and `prev`. 
- `head.prev` directly references the tail node in $O(1)$.
- `tail.next` directly references the `head` node in $O(1)$.
- There is **never** a `None` pointer in a populated list.
- `current` references the currently playing node.

```
                  +===================================================================+
                  |                                                                   |
                  v                                                                   |  (Tail.next wraps to Head)
          +---------------+         +---------------+         +---------------+       |
   +----->|  Head (Pos 1) |<------->| Current (Pos2)|<------->|  Tail (Pos 3) |-------+
   |      |  "Song A"     |         |  "Song B"     |         |  "Song C"     |
   |      +---------------+         +---------------+         +---------------+
   |              ^                                                   |
   |              |                                                   v
   +==============+===================================================+
                  (Head.prev wraps to Tail)
```

---

## ⏱️ Time Complexity Analysis

| Operation | Time Complexity | Detailed Analysis |
| :--- | :---: | :--- |
| **`next_track()`** | $\mathcal{O}(1)$ | Updates pointer: `current = current.next`. Wraps from tail to head with no boundary check. |
| **`prev_track()`** | $\mathcal{O}(1)$ | Updates pointer: `current = current.prev`. Wraps from head to tail with no boundary check. |
| **`insert_at_end()`** | $\mathcal{O}(1)$ | Tail is instantly accessed via `head.prev`. Relinks 4 pointers in constant time. |
| **`insert_at_position()`**| $\mathcal{O}(n) + \mathcal{O}(1)$ | $\mathcal{O}(n)$ to locate target node, $\mathcal{O}(1)$ to relink pointers. |
| **`delete_by_id()`** | $\mathcal{O}(n) + \mathcal{O}(1)$ | $\mathcal{O}(n)$ to locate node by ID, $\mathcal{O}(1)$ to bridge `A.next = C` and `C.prev = A`. |
| **`move(pos_a, pos_b)`** | $\mathcal{O}(n) + \mathcal{O}(1)$ | $\mathcal{O}(n)$ to locate both positions, $\mathcal{O}(1)$ pointer relinking (no new allocation). |
| **`to_list()` / display** | $\mathcal{O}(n)$ | Single do-while pass from `head` until `curr is head`. |

### Key DSA Takeaway: Linked List vs. Array Shifting
- In a dynamic array / Python `list`, inserting or deleting at index $i$ requires **shifting all subsequent elements** $\mathcal{O}(n)$ in memory.
- In a Linked List, once you hold a pointer to a node, **inserting, deleting, or moving that node is purely $\mathcal{O}(1)$ pointer relinking** without shifting other elements.

---

## 🛠️ Project Directory Structure

```
playlist_manager/
  manage.py                    # Django management script
  requirements.txt             # Project requirements (Django only)
  README.md                    # Project documentation & DSA guide
  config/
    settings.py                # Django settings (installed apps, templates)
    urls.py                    # Root URL router
  playlist/
    cdll.py                    # Node & CircularDoublyLinkedList (pure Python, 0 Django)
    models.py                  # Persistent models (Track, PlaylistState)
    services.py                # CDLL <-> SQLite Bridge
    views.py                   # Thin HTTP & JSON REST API views
    urls.py                    # App-level routing
    templates/playlist/
      index.html               # Single-page interactive web UI
    static/playlist/
      style.css                # Custom CSS styling (dark glassmorphism)
      app.js                   # Interactive UI, SVG Ring, Drag-and-Drop, CLI Console
    tests/
      test_cdll.py             # Pure Python unittest suite (22 tests, no Django)
      test_api.py              # Django TestCase suite (8 API tests)
```

---

## 🚀 Setup & Installation Instructions

### Prerequisites
- Python 3.11+ installed.

### 1. Open Terminal in the Project Directory
```bash
cd playlist_manager
```

### 2. (Optional) Create & Activate a Virtual Environment
**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
python manage.py migrate
```

### 5. Run the Server
```bash
python manage.py runserver
```

Open your browser at: **`http://127.0.0.1:8000/`**

---

## 🧪 Running the Test Suites

### Run Pure CDLL Data Structure Tests (Zero Django)
```bash
python -m unittest playlist/tests/test_cdll.py
```
*Executes 22 pure unit tests verifying ring wrap-around, pointer invariants, edge-case deletions, and pointer relocations with `verify_integrity()` after every mutation.*

### Run Full Django API & Integration Tests
```bash
python manage.py test
```
*Executes all 30 tests (both pure CDLL unit tests and HTTP API integration tests).*

---

## 💻 DSA Command Console (CLI Commands)

The interactive terminal at the bottom-right of the web page supports the following live commands:

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `next` | none | $\mathcal{O}(1)$ Advance: `current = current.next` |
| `prev` | none | $\mathcal{O}(1)$ Rewind: `current = current.prev` |
| `play` | `[track_id]` | Toggles play/pause, or jumps directly to a specific track ID |
| `pause`| none | Pauses playback simulation |
| `insert` | `<title> <artist> <duration> [position]` | Inserts a new song node into the CDLL |
| `delete` | `<track_id>` | Unlinks and deletes the specified track node |
| `move` | `<pos_a> <pos_b>` | Unlinks node at `pos_a` and relinks at `pos_b` without reallocation |
| `help` | none | Prints the full command reference |
| `clear`| none | Clears the terminal screen |

---

## 🎓 Viva Questions & Answers for Students

### Q1: Why use a Circular Doubly Linked List instead of a standard Singly Linked List?
> **Answer:** 
> 1. In a playlist, users expect seamless wrap-around looping from the end back to the start. In a Singly Linked List, reaching the tail requires $\mathcal{O}(n)$ traversal from head, and moving backward to the previous song is impossible without another $\mathcal{O}(n)$ search.
> 2. With a CDLL, both `current.next` and `current.prev` are constant time $\mathcal{O}(1)$. Additionally, accessing the tail node takes $\mathcal{O}(1)$ time directly via `head.prev`.

### Q2: Why are there no `node.next is None` checks during navigation?
> **Answer:** 
> Because the list is circular. Every node's `next` points to a valid node (in a 1-node list, it points to itself; in a multi-node list, the tail's `next` points to `head`). Boundary checks are structurally unnecessary—the pointers naturally cycle indefinitely.

### Q3: Why does `move(pos_a, pos_b)` relink pointers instead of creating a new Node?
> **Answer:** 
> Allocating a new node wastes memory and creates unnecessary garbage collection overhead. In DSA, moving an element in a linked list simply requires unlinking the existing node from its current neighbors (`prev.next = next`, `next.prev = prev`) and inserting it between the new neighbors. The node's ID, metadata, and object identity remain preserved.

### Q4: Why is a Service Layer necessary between Django and the CDLL?
> **Answer:** 
> Web applications use stateless request-response cycles. Memory is cleared between requests. The service layer acts as a bridge: it loads ordered track records from SQLite, populates the in-memory CDLL, invokes the algorithmic pointer methods, and persists the resulting sequence and playback state back to the database. This keeps views thin and decoupled from data structure internals.

