import unittest

from src.config import load_quant_firms_config, load_sources_config


class QuantFirmsConfigTests(unittest.TestCase):
    def test_catalog_contains_fifty_unique_firms(self) -> None:
        firms = load_quant_firms_config().firms

        self.assertEqual(len(firms), 50)
        self.assertEqual(len({firm.name for firm in firms}), 50)
        self.assertTrue(all(firm.careers_url.startswith("https://") for firm in firms))

    def test_monitored_greenhouse_firms_use_configured_boards(self) -> None:
        firms = load_quant_firms_config().firms
        source_boards = {
            board.slug for board in load_sources_config().sources["greenhouse"].boards
        }
        catalog_boards = {
            firm.board_slug
            for firm in firms
            if firm.monitoring in {"greenhouse", "greenhouse_partial"}
        }

        self.assertNotIn(None, catalog_boards)
        self.assertEqual(catalog_boards, source_boards)


if __name__ == "__main__":
    unittest.main()
