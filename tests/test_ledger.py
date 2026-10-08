"""Ledger correctness using synthetic trade outcomes, never historical claims."""
import unittest
from decimal import localcontext
from lab.ledger import summarize_ledger


def row(day, pnl, costs=10, mode='paper', identifier=None):
    return dict(id=identifier, mode=mode, closed_at=f'2026-01-{day:02d}T12:00:00Z',
                pnl_clp=pnl, costs_clp=costs)


class LedgerTests(unittest.TestCase):
    def test_net_pnl_does_not_subtract_costs_twice(self):
        result = summarize_ledger([row(1, 100), row(2, -50)], 1000)
        self.assertEqual(result['net_pnl_clp'], 50)
        self.assertEqual(result['costs_clp'], 20)
        self.assertEqual(result['equity_clp'], 1050)
        self.assertEqual(result['return_fraction'], 0.05)
        self.assertEqual(result['win_rate'], 0.5)
        self.assertEqual(result['profit_factor'], 2)

    def test_drawdown_uses_peak_and_chronological_order(self):
        result = summarize_ledger([row(3, 30), row(1, 100), row(2, -200)], 1000)
        self.assertEqual(result['max_drawdown_clp'], 200)
        self.assertAlmostEqual(result['max_drawdown_fraction'], 200 / 1100)
        self.assertEqual(result['drawdown_basis'], 'closed_trades_only')

    def test_marked_curve_includes_open_position_drawdowns(self):
        result = summarize_ledger([row(2, 50)], 1000, equity_curve=[
            dict(timestamp='2026-01-01T10:00:00Z', equity_clp=1100),
            dict(timestamp='2026-01-01T11:00:00Z', equity_clp=850),
            dict(timestamp='2026-01-02T13:00:00Z', equity_clp=1050),
        ])
        self.assertEqual(result['max_drawdown_clp'], 250)
        self.assertEqual(result['drawdown_basis'], 'marked_equity')

    def test_unknown_capital_leaves_relative_metrics_unavailable(self):
        result = summarize_ledger([row(1, 100)], None)
        self.assertEqual(result['status'], 'DATOS_INSUFICIENTES')
        self.assertEqual(result['net_pnl_clp'], 100)
        self.assertIsNone(result['return_fraction'])
        self.assertIsNone(result['equity_clp'])
        self.assertIsNone(result['max_drawdown_fraction'])

    def test_empty_ledger_is_not_a_winning_strategy(self):
        result = summarize_ledger([], 1000)
        self.assertEqual(result['status'], 'SIN_OPERACIONES')
        self.assertIsNone(result['win_rate'])
        self.assertIsNone(result['average_pnl_clp'])
        self.assertEqual(result['return_fraction'], 0)
        self.assertIsNone(summarize_ledger([], None)['return_fraction'])

    def test_mixed_real_rows_are_rejected(self):
        with self.assertRaises(ValueError):
            summarize_ledger([row(1, 100), row(2, 100, mode='real')], 1000)

    def test_duplicate_trade_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            summarize_ledger([row(1, 100, identifier='a'), row(2, 100, identifier='a')], 1000)

    def test_costs_pnl_and_dates_require_valid_data(self):
        for key, value in (('costs_clp', -1), ('pnl_clp', float('inf')),
                           ('closed_at', '2026-01-01T12:00:00')):
            with self.subTest(key=key):
                invalid = row(1, 100)
                invalid[key] = value
                with self.assertRaises(ValueError):
                    summarize_ledger([invalid], 1000)

    def test_equity_curve_real_mode_and_nonchronological_dates_reject(self):
        for curve in ([dict(timestamp='2026-01-01T10:00:00Z', equity_clp=1000, mode='real')],
                      [dict(timestamp='2026-01-02T10:00:00Z', equity_clp=1000),
                       dict(timestamp='2026-01-01T10:00:00Z', equity_clp=1100)]):
            with self.subTest(curve=curve):
                with self.assertRaises(ValueError):
                    summarize_ledger([], 1000, curve)

    def test_huge_exponents_and_decimal_arithmetic_are_controlled(self):
        with self.assertRaises(ValueError):
            summarize_ledger([row(1, '1e1000000')], 1000)
        with localcontext() as context:
            context.Emax = 5
            with self.assertRaises(ValueError):
                summarize_ledger([row(1, 900000), row(2, 900000)], 1000)

    def test_numeric_marked_curve_and_losses_beyond_capital_are_reported(self):
        result = summarize_ledger([], 1000, [1000, -100])
        self.assertEqual(result['return_fraction'], -1.1)
        self.assertEqual(result['max_drawdown_fraction'], 1.1)


if __name__ == '__main__':
    unittest.main()

