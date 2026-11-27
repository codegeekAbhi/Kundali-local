import subprocess
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from kundli import active_dasha_sequence, next_sign_change
from numerology import date_numbers


class CalculationsTest(unittest.TestCase):
    def test_numerology(self):
        self.assertEqual(
            date_numbers(date(2000, 1, 1), 2026),
            {"Life Path": 4, "Birth Day": 1, "Personal Year": 3},
        )

    def test_dasha_boundary(self):
        start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        sequence, boundary = active_dasha_sequence(0, start, start)
        self.assertEqual(sequence, "Ketu / Ketu / Ketu")
        self.assertEqual(active_dasha_sequence(0, start, boundary)[0], "Ketu / Ketu / Venus")

    def test_sign_crossing(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        crossing = start + timedelta(hours=13)
        sign, when = next_sign_change(lambda instant: 1 if instant >= crossing else 0, start)
        self.assertEqual(sign, 1)
        self.assertLessEqual(abs(when - crossing), timedelta(minutes=1))

    def test_sample_chart(self):
        output = subprocess.check_output(
            [sys.executable, str(Path(__file__).with_name("kundli.py")),
             "2000-01-01T12:00", "Asia/Kolkata", "28.6139", "77.2090",
             "--as-of", "2026-11-26", "--transits", "--timeline", "180",
             "--reading", "offline"],
            text=True,
        )
        self.assertIn("Saturn / Venus / Venus", output)
        self.assertIn("Jupiter: Leo, house 6 from Lagna", output)
        self.assertIn("Next sign: Cancer around 2027-01-24", output)
        self.assertIn("Reading (offline)", output)


if __name__ == "__main__":
    unittest.main()
