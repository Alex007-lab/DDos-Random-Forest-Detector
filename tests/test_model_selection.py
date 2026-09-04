import sys
import unittest

from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "detector"))

from train_model import select_threshold  # noqa: E402


class ModelSelectionTests(unittest.TestCase):
    def test_baseline_threshold_is_not_limited_to_probability_range(self):
        labels = np.asarray(["normal", "normal", "attack", "attack"])
        requests_per_second = np.asarray([1.0, 3.0, 100.0, 120.0])
        result = select_threshold(labels, requests_per_second)
        self.assertGreater(result["threshold"], 3.0)
        self.assertLessEqual(result["threshold"], 100.0)
        self.assertEqual(result["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
