import importlib
import sys
import unittest


class ProjectSkeletonTest(unittest.TestCase):
    def test_runtime_is_python_312(self) -> None:
        self.assertEqual(sys.version_info[:2], (3, 12))

    def test_fastapi_app_module_is_importable(self) -> None:
        module = importlib.import_module("app.main")
        self.assertTrue(hasattr(module, "app"))


if __name__ == "__main__":
    unittest.main()
