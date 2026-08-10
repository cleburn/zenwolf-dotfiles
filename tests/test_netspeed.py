import runpy
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "home/.local/bin/zenwolf-netspeed"
)
APP = runpy.run_path(str(SCRIPT))

RATE_CONNECTION = APP["rate_connection"]
FAST_RATING = ("fast as fuk boi", APP["GREEN"])
MEH_RATING = ("meh", APP["GOLD"])
SHITTY_RATING = ("shitty", APP["RED"])


class RatingTests(unittest.TestCase):
    def test_fast_boundary(self) -> None:
        self.assertEqual(
            RATE_CONNECTION(100.0, 20.0, 75.0),
            FAST_RATING,
        )

    def test_meh_boundary(self) -> None:
        self.assertEqual(
            RATE_CONNECTION(25.0, 5.0, 100.0),
            MEH_RATING,
        )

    def test_shitty_when_any_meh_requirement_fails(self) -> None:
        cases = (
            (24.9, 100.0, 10.0),
            (100.0, 4.9, 10.0),
            (100.0, 100.0, 100.1),
        )

        for download, upload, ping in cases:
            with self.subTest(
                download=download,
                upload=upload,
                ping=ping,
            ):
                self.assertEqual(
                    RATE_CONNECTION(download, upload, ping),
                    SHITTY_RATING,
                )


if __name__ == "__main__":
    unittest.main()