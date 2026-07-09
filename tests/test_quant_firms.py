import unittest

from src.config import load_quant_firms_config, load_sources_config


class QuantFirmsConfigTests(unittest.TestCase):
    def test_catalog_contains_large_unique_firm_universe(self) -> None:
        firms = load_quant_firms_config().firms

        self.assertGreaterEqual(len(firms), 65)
        self.assertEqual(len({firm.name for firm in firms}), len(firms))
        self.assertTrue(all(firm.careers_url.startswith("https://") for firm in firms))

    def test_monitored_firms_use_configured_boards(self) -> None:
        firms = load_quant_firms_config().firms
        sources = load_sources_config().sources
        monitored_types = {"ashby", "breezy", "greenhouse", "greenhouse_partial", "lever", "pinpoint", "successfactors"}

        for firm in firms:
            if firm.monitoring not in monitored_types:
                continue
            source_key = "greenhouse" if firm.monitoring == "greenhouse_partial" else firm.monitoring
            configured_boards = {board.slug for board in sources[source_key].boards}
            firm_boards = set(firm.board_slugs)
            if firm.board_slug:
                firm_boards.add(firm.board_slug)

            self.assertTrue(firm_boards, firm.name)
            self.assertTrue(firm_boards <= configured_boards, firm.name)


if __name__ == "__main__":
    unittest.main()
