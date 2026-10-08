"""User-flow checks with fictional session data; no browser or external API."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


class DashboardTests(unittest.TestCase):
    def test_empty_session_has_four_views_and_blocks_operations(self):
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([tab.label for tab in app.tabs],
                         ["Resumen", "Mercado", "Operaciones", "Equipo"])
        self.assertTrue(any("NO OPERAR" in error.value for error in app.error))
        self.assertEqual(app.session_state["snapshot"]["opportunities"], [])
        self.assertEqual(len(app.metric), 7)

    def test_synthetic_example_can_be_loaded_and_cleared(self):
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        app.sidebar.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.session_state["snapshot"]["synthetic"])
        self.assertEqual(len(app.session_state["snapshot"]["trades"]), 3)
        self.assertTrue(any("SINTÉTICO" in warning.value for warning in app.warning))
        self.assertTrue(any("NO OPERAR" in error.value for error in app.error))
        app.sidebar.button[1].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["snapshot"]["trades"], [])
        self.assertFalse(app.session_state["snapshot"]["synthetic"])


if __name__ == "__main__":
    unittest.main()
