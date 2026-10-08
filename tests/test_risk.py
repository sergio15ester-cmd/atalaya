"""Synthetic unit fixtures only: these values are not market quotes or user capital."""
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lab.risk import evaluate_risk


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        self.policy = json.loads((Path(__file__).parents[1] / 'config' / 'risk-policy.example.json').read_text(encoding='utf-8-sig'))
        self.policy.update(status='approved_paper', capital_initial_clp=80000,
                           team_members=[1, 2, 3], data_provider='synthetic-fixture',
                           execution_provider='synthetic-fixture', session_timezone='UTC',
                           session_start_local='08:00', session_end_local='16:00')
        self.policy['data_requirements']['maximum_quote_age_seconds'] = 30
        self.policy['execution_cost_model'].update(cost_schedule_source='synthetic-fees',
                  cost_schedule_verified_at_utc='2026-01-01T11:59:00Z', maximum_cost_age_seconds=86400)
        self.account = dict(capital_initial_clp=80000, session_start_equity_clp=80000,
                            cash_clp=80000, open_exposure_clp=0, open_risk_clp=0,
                            day_loss_clp=0, high_water_clp=80000, equity_clp=80000,
                            entries_today=0, open_positions=0, strategy_approved=True)
        self.opportunity = dict(bid=999, ask=1000, stop=995, target=1018,
             quantity_step=1, min_quantity=1, min_notional=1000,
             commission_rate=0, min_fee=0, slippage_fraction=0,
             fx_rate=1, fx_cost_fraction=0, source='synthetic-fixture',
             market_timestamp='2026-01-01T11:59:59Z', received_timestamp='2026-01-01T12:00:00Z',
             expires_at='2026-01-01T12:00:30Z', fx_source='identity:CLP',
             fx_timestamp='2026-01-01T11:59:59Z', cost_source='synthetic-fees',
             cost_verified_at='2026-01-01T11:59:00Z', currency='CLP', side='buy',
             instrument_type='spot', leveraged=False, liquidity_verified=True,
             coverage='synthetic book only')

    def evaluate(self):
        return evaluate_risk(self.policy, self.account, self.opportunity, self.now)

    def test_approved_size_respects_exposure_and_risk(self):
        result = self.evaluate()
        self.assertEqual(result['status'], 'APTO_PARA_SIMULAR')
        self.assertEqual(result['quantity'], 16)
        self.assertEqual(result['exposure_clp'], 16000)
        self.assertEqual(result['risk_clp'], 80)
        self.assertEqual(result['reward_clp'], 288)
        self.assertEqual(result['net_reward_risk'], 3.6)

    def test_public_draft_with_unknown_capital_never_admits(self):
        self.policy.update(status='draft', capital_initial_clp=None)
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_known_capital_without_strategy_approval_never_admits(self):
        self.account['strategy_approved'] = False
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_fee_minimums_applied_to_both_legs_once(self):
        self.opportunity['min_fee'] = 1
        result = self.evaluate()
        self.assertEqual(result['costs_clp'], 2)
        self.assertEqual(result['risk_clp'], 82)
        self.assertEqual(result['reward_clp'], 286)
        self.assertEqual(result['entry_cash_clp'], 16001)

    def test_minimum_fees_can_make_every_quantity_infeasible(self):
        self.opportunity['min_fee'] = 26
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_spread_is_not_counted_twice(self):
        self.opportunity.update(quantity=1, stop=990, target=1021)
        result = self.evaluate()
        self.assertEqual(result['risk_clp'], 10)
        self.assertEqual(result['reward_clp'], 21)
        self.assertEqual(result['costs_clp'], 0)

    def test_slippage_fx_costs_and_rounding(self):
        self.opportunity.update(currency='USD', bid=0.999, ask=1, stop=0.995,
             target=1.018, min_notional=1, fx_rate=1000, fx_cost_fraction=0.0001,
             slippage_fraction=0.0001, quantity_step=0.01)
        result = self.evaluate()
        self.assertEqual(result['status'], 'APTO_PARA_SIMULAR')
        self.assertEqual(result['quantity'], 15.99)
        self.assertGreater(result['costs_clp'], 0)
        self.assertLessEqual(result['exposure_clp'], 16000)
        self.assertLessEqual(result['entry_cash_clp'], 80000)

    def test_settled_cash_includes_entry_fees(self):
        self.account['cash_clp'] = 16000
        self.opportunity['min_fee'] = 1
        result = self.evaluate()
        self.assertEqual(result['quantity'], 15)
        self.assertLessEqual(result['entry_cash_clp'], 16000)

    def test_requested_fractional_quantity_not_aligned_rejects(self):
        self.opportunity['quantity'] = 1.5
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_minimum_notional_rejects_if_above_exposure_budget(self):
        self.opportunity['min_notional'] = 17000
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_remaining_daily_budget_limits_new_and_open_risk(self):
        self.account.update(day_loss_clp=550, equity_clp=79450, open_risk_clp=45)
        result = self.evaluate()
        self.assertEqual(result['status'], 'APTO_PARA_SIMULAR')
        self.assertEqual(result['risk_clp'], 5)
        self.assertLessEqual(result['risk_clp'] + self.account['open_risk_clp'] + 550, 600)

    def test_marked_loss_cannot_be_hidden_by_day_loss_field(self):
        self.account.update(day_loss_clp=0, equity_clp=79399)
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_maximum_initial_loss_and_peak_drawdown_block(self):
        for equity, start, peak in ((76000, 76000, 80000), (84000, 84000, 90000)):
            with self.subTest(equity=equity):
                self.account.update(equity_clp=equity, session_start_equity_clp=start, high_water_clp=peak)
                self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_risk_base_is_minimum_of_initial_and_session_equity(self):
        self.account.update(equity_clp=79000, session_start_equity_clp=79000)
        result = self.evaluate()
        self.assertEqual(result['quantity'], 15)
        self.assertLessEqual(result['exposure_clp'], 15800)

    def test_stale_quotes_fx_and_expired_proposals_reject(self):
        for key in ('market_timestamp', 'fx_timestamp', 'expires_at'):
            with self.subTest(key=key):
                original = self.opportunity[key]
                self.opportunity[key] = '2026-01-01T11:59:00Z'
                self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')
                self.opportunity[key] = original

    def test_naive_or_future_times_reject(self):
        for value in ('2026-01-01T11:59:59', '2026-01-01T12:00:01Z'):
            self.opportunity['market_timestamp'] = value
            self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_cost_profile_must_match_and_be_fresh(self):
        self.opportunity['cost_source'] = 'other-fees'
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')
        self.opportunity['cost_source'] = 'synthetic-fees'
        self.policy['execution_cost_model']['maximum_cost_age_seconds'] = 30
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_session_end_is_exclusive(self):
        self.now = self.now.replace(hour=16)
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_real_leverage_short_unknown_liquidity_and_currency_reject(self):
        for key, value in (('side', 'sell'), ('leveraged', True),
                           ('liquidity_verified', False), ('currency', 'UNKNOWN'),
                           ('instrument_type', 'derivative')):
            with self.subTest(key=key):
                original = self.opportunity[key]
                self.opportunity[key] = value
                self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')
                self.opportunity[key] = original
        self.policy['execution']['mode'] = 'real'
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_position_and_entry_limits(self):
        self.account['entries_today'] = 3
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')
        self.account.update(entries_today=0, open_positions=2)
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_nan_boolean_and_extreme_precision_do_not_admit(self):
        for key, value in (('ask', float('nan')), ('commission_rate', True),
                           ('quantity_step', '1e-1000000'), ('ask', '1e1000000')):
            with self.subTest(key=key):
                original = self.opportunity[key]
                self.opportunity[key] = value
                self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')
                self.opportunity[key] = original

    def test_decimal_modulo_precision_failure_is_controlled(self):
        self.opportunity.update(quantity='1e18', quantity_step='1e-18')
        result = self.evaluate()
        self.assertEqual(result['status'], 'NO_OPERAR')
        self.assertIn('aritmética', result['reasons'][0])

    def test_huge_fx_exponent_is_controlled(self):
        self.opportunity.update(currency='USD', fx_rate='1e1000000')
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_unknown_risk_base_method_is_rejected(self):
        self.policy['risk_base']['method'] = 'unknown_method'
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_missing_costs_are_not_assumed_zero(self):
        self.opportunity.pop('commission_rate')
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_insufficient_net_reward_rejects(self):
        self.opportunity['target'] = 1009
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_identity_and_account_consistency(self):
        self.policy['team_members'] = [1, 1, 2]
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')
        self.policy['team_members'] = [1, 2, 3]
        self.account['capital_initial_clp'] = 50000
        self.assertEqual(self.evaluate()['status'], 'NO_OPERAR')

    def test_inputs_not_mutated(self):
        before = copy.deepcopy((self.policy, self.account, self.opportunity))
        self.evaluate()
        self.assertEqual((self.policy, self.account, self.opportunity), before)


if __name__ == '__main__':
    unittest.main()


