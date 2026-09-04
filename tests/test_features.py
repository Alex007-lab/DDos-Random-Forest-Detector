import json
import sys
import unittest

from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "detector"))

from features import (  # noqa: E402
    calculate_features,
    group_events,
    parse_event_line,
)


class FeatureTests(unittest.TestCase):
    def event(self, timestamp, status=200, uri="/"):
        return parse_event_line(
            json.dumps(
                {
                    "timestamp": timestamp,
                    "remote_addr": "172.20.0.4",
                    "method": "GET",
                    "uri": uri,
                    "protocol": "HTTP/1.1",
                    "status": status,
                    "bytes_sent": 100,
                    "request_length": 50,
                    "request_time": 0.01,
                    "user_agent": "unit-test",
                    "connection": 1,
                    "connection_requests": 1,
                }
            )
        )

    def test_groups_events_in_aligned_windows(self):
        events = [
            self.event("2026-08-31T10:00:01+00:00"),
            self.event("2026-08-31T10:00:09+00:00"),
            self.event("2026-08-31T10:00:10+00:00"),
        ]
        windows = group_events(events, 10)
        self.assertEqual([len(value) for value in windows.values()], [2, 1])

    def test_calculates_ratios_and_unique_uris(self):
        events = [
            self.event("2026-08-31T10:00:01+00:00", 200, "/"),
            self.event("2026-08-31T10:00:02+00:00", 404, "/missing"),
        ]
        row = calculate_features(
            datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc),
            events,
            10,
            "normal",
        )
        self.assertEqual(row["request_count"], 2)
        self.assertEqual(row["requests_per_second"], 0.2)
        self.assertEqual(row["error_4xx_ratio"], 0.5)
        self.assertEqual(row["unique_uris"], 2)

    def test_rejects_missing_required_field(self):
        with self.assertRaises(ValueError):
            parse_event_line(json.dumps({"timestamp": "2026-08-31T10:00:00Z"}))


if __name__ == "__main__":
    unittest.main()
