import sqlite3
import json
from typing import List, Tuple, Optional
from pathlib import Path

DB_SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    address TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,
    path TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(person_id) REFERENCES persons(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,
    photo_id INTEGER,
    vector TEXT NOT NULL, -- JSON serialized list
    ratios TEXT, -- JSON serialized dict of face ratios
    model TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(person_id) REFERENCES persons(id) ON DELETE CASCADE,
    FOREIGN KEY(photo_id) REFERENCES photos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,
    fingerprint_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(person_id) REFERENCES persons(id) ON DELETE CASCADE
);
'''


def init_db(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(DB_SCHEMA)
    conn.commit()
    conn.close()


def add_admin(db_path: str, username: str, password_hash: str, display_name: Optional[str] = None) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO admins (username, password_hash, display_name) VALUES (?, ?, ?)",
        (username, password_hash, display_name),
    )
    admin_id = cur.lastrowid
    conn.commit()
    conn.close()
    return admin_id


def get_admin_by_username(db_path: str, username: str) -> Optional[dict]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM admins WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_admin_count(db_path: str) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM admins")
    row = cur.fetchone()
    conn.close()
    return int(row["total"] if row else 0)


def get_person_counts(db_path: str) -> dict:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM persons")
    persons = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM photos")
    photos = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM fingerprints")
    fingerprints = cur.fetchone()["total"]
    conn.close()
    return {
        "persons": int(persons or 0),
        "photos": int(photos or 0),
        "fingerprints": int(fingerprints or 0),
    }


def get_conn(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def add_person(db_path: str, name: str, age: Optional[int], gender: Optional[str], address: Optional[str], notes: Optional[str]) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO persons (name, age, gender, address, notes) VALUES (?, ?, ?, ?, ?)",
                (name, age, gender, address, notes))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def update_person(db_path: str, person_id: int, name: str, age: Optional[int], gender: Optional[str], address: Optional[str], notes: Optional[str]) -> bool:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE persons SET name = ?, age = ?, gender = ?, address = ?, notes = ? WHERE id = ?",
        (name, age, gender, address, notes, person_id),
    )
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def add_photo(db_path: str, person_id: int, path: str) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO photos (person_id, path) VALUES (?, ?)", (person_id, path))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def get_photos_by_person_id(db_path: str, person_id: int) -> List[dict]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM photos WHERE person_id = ? ORDER BY created_at ASC, id ASC", (person_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_primary_photo_by_person_id(db_path: str, person_id: int) -> Optional[dict]:
    photos = get_photos_by_person_id(db_path, person_id)
    if photos:
        return photos[0]
    return None


def get_photo_by_id(db_path: str, photo_id: int) -> Optional[dict]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM photos WHERE id = ?", (photo_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def update_photo_person(db_path: str, photo_id: int, person_id: Optional[int]) -> bool:
    """Associate an existing photo with a person (or set to NULL when person_id is None)."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE photos SET person_id = ? WHERE id = ?", (person_id, photo_id))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def add_photos(db_path: str, person_id: int, paths: List[str]) -> List[int]:
    photo_ids = []
    for path in paths:
        photo_ids.append(add_photo(db_path, person_id, path))
    return photo_ids


def add_embedding(db_path: str, person_id: int, photo_id: int, vector: List[float], ratios: dict = None, model: str = "fallback") -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    ratios_json = json.dumps(ratios) if ratios is not None else None
    cur.execute("INSERT INTO embeddings (person_id, photo_id, vector, ratios, model) VALUES (?, ?, ?, ?, ?)",
                (person_id, photo_id, json.dumps(vector), ratios_json, model))
    eid = cur.lastrowid
    conn.commit()
    conn.close()
    return eid


def get_all_embeddings(db_path: str) -> List[Tuple[int, int, int, List[float], dict]]:
    """Return list of tuples (embedding_id, person_id, photo_id, vector, ratios)"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, person_id, photo_id, vector, ratios FROM embeddings")
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        ratios = json.loads(r[4]) if r[4] else {}
        result.append((r[0], r[1], r[2], json.loads(r[3]), ratios))
    return result


def get_person_by_id(db_path: str, person_id: int) -> Optional[dict]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM persons WHERE id = ?", (person_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_all_persons(db_path: str) -> List[dict]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM persons")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_fingerprint(db_path: str, person_id: int, fingerprint_data: str) -> int:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO fingerprints (person_id, fingerprint_data) VALUES (?, ?)",
                (person_id, fingerprint_data))
    fid = cur.lastrowid
    conn.commit()
    conn.close()
    return fid


def get_fingerprints_by_person_id(db_path: str, person_id: int) -> List[dict]:
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM fingerprints WHERE person_id = ? ORDER BY created_at ASC, id ASC", (person_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_fingerprints(db_path: str, person_id: int, fingerprint_data_list: List[str]) -> List[int]:
    fingerprint_ids = []
    for fingerprint_data in fingerprint_data_list:
        fingerprint_ids.append(add_fingerprint(db_path, person_id, fingerprint_data))
    return fingerprint_ids


def get_person_details(db_path: str, person_id: int) -> Optional[dict]:
    person = get_person_by_id(db_path, person_id)
    if not person:
        return None

    photos = get_photos_by_person_id(db_path, person_id)
    fingerprints = get_fingerprints_by_person_id(db_path, person_id)
    person["photos"] = photos
    person["fingerprints"] = fingerprints
    person["photo_count"] = len(photos)
    person["fingerprint_count"] = len(fingerprints)
    return person


def get_all_persons_with_counts(db_path: str) -> List[dict]:
    persons = get_all_persons(db_path)
    for person in persons:
        photos = get_photos_by_person_id(db_path, person["id"])
        fingerprints = get_fingerprints_by_person_id(db_path, person["id"])
        person["photo_count"] = len(photos)
        person["fingerprint_count"] = len(fingerprints)
    return persons
