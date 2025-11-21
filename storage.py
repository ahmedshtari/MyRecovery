# storage.py

"""
Simple storage layer for the recovery app.

We store everything in a single JSON file: data.json

Structure:
{
  "sets": [
      {
        "user_id": "Ahmed",
        "exercise_id": "bench_press",
        "reps": 8,
        "weight": 80.0,
        "rir": 2,
        "timestamp": "2025-11-21T12:34:56.789123"
      },
      ...
  ],
  "daily": [
      {
        "user_id": "dyar",
        "date": "2025-11-21",
        "sleep_hours": 7.5,
        "steps": 9500
      },
      ...
  ]
}
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# data.json will live in the same folder as this file
DATA_FILE = Path(__file__).with_name("data.json")


def _load_data() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        return {"sets": [], "daily": []}
    text = DATA_FILE.read_text(encoding="utf-8")
    if not text.strip():
        return {"sets": [], "daily": []}
    return json.loads(text)


def _save_data(data: Dict[str, Any]) -> None:
    DATA_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def log_set(
    user_id: str,
    exercise_id: str,
    reps: int,
    weight: float,
    rir: Optional[int],
    timestamp: Optional[datetime] = None,
) -> None:
    """
    Append a logged set to data.json.
    - rir can be None if you didn't track it.
    - timestamp can be given, or defaults to now().
    """
    if timestamp is None:
        timestamp = datetime.now()

    data = _load_data()
    data.setdefault("sets", [])
    data["sets"].append(
        {
            "user_id": user_id,
            "exercise_id": exercise_id,
            "reps": int(reps),
            "weight": float(weight),
            "rir": int(rir) if rir is not None else None,
            "timestamp": timestamp.isoformat(),
        }
    )
    _save_data(data)


def log_daily_recovery(
    user_id: str,
    sleep_hours: Optional[float],
    steps: Optional[int],
) -> None:
    """
    Store sleep + steps for *today* for this user.
    If there's already an entry for today, overwrite it.
    """
    data = _load_data()
    data.setdefault("daily", [])
    today = datetime.now().date().isoformat()

    # remove existing entry for this user & date
    data["daily"] = [
        d
        for d in data["daily"]
        if not (d.get("user_id") == user_id and d.get("date") == today)
    ]

    data["daily"].append(
        {
            "user_id": user_id,
            "date": today,
            "sleep_hours": float(sleep_hours) if sleep_hours is not None else None,
            "steps": int(steps) if steps is not None else None,
        }
    )
    _save_data(data)


def get_all_sets() -> List[Dict[str, Any]]:
    data = _load_data()
    return data.get("sets", [])


def get_all_daily() -> List[Dict[str, Any]]:
    data = _load_data()
    return data.get("daily", [])


def delete_set_by_timestamp(user_id: str, timestamp: str) -> bool:
    """
    Delete a single set for this user matching the exact timestamp.
    Returns True if a set was removed, False otherwise.
    """
    data = _load_data()
    before = len(data.get("sets", []))
    data["sets"] = [
        s
        for s in data.get("sets", [])
        if not (s.get("user_id") == user_id and s.get("timestamp") == timestamp)
    ]
    after = len(data["sets"])
    if after < before:
        _save_data(data)
        return True
    return False

