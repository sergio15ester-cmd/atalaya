"""Deterministic long-only paper risk checks; no API calls or real orders.

Schema and prices:
- policy: risk-policy.example.json, explicitly approved_paper and complete.
- account: capital_initial_clp, session_start_equity_clp, cash_clp,
  open_exposure_clp, open_risk_clp, day_loss_clp, high_water_clp, equity_clp,
  entries_today, open_positions and strategy_approved=True.
- opportunity: bid, ask, stop, target (executable bid at exit), quantity_step,
  min_quantity, min_notional (quote currency), commission_rate, min_fee
  (per order, quote currency), slippage_fraction, fx_rate (CLP/quote currency),
  fx_cost_fraction, source, market_timestamp, received_timestamp, expires_at,
  fx_source, fx_timestamp, cost_source, cost_verified_at; currency CLP/USD,
  side='buy', instrument_type spot/stock/etf, leveraged=False,
  liquidity_verified=True and nonempty coverage.
  Policy execution_cost_model.maximum_cost_age_seconds must be configured.
  account.strategy_approved is a caller-supplied claim: callers must derive it
  from current verified human governance, not untrusted uploaded input.
  FX remains the snapshot rate in both outcomes; FX risk is not forecast.
  Optional quantity requests that exact size; otherwise choose largest size
  satisfying budgets, rounded DOWN to quantity_step. Timestamps are aware ISO.

Commissions and FX costs apply to both legs. Spread is already in ask/bid:
never add it again. P&L and all budgets are CLP, before taxes. Admission is
only a calculation for simulation, never authorization or order execution.
"""
from datetime import datetime, time, timezone
from decimal import Decimal, DecimalException, ROUND_CEILING, ROUND_FLOOR
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ZERO = Decimal('0')
ONE = Decimal('1')


class InvalidInput(ValueError):
    pass


def _number(value, field, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or value is None:
        raise InvalidInput(f'{field}: número requerido')
    try:
        result = Decimal(str(value))
    except (DecimalException, ValueError, TypeError):
        raise InvalidInput(f'{field}: número inválido') from None
    if result.is_finite() and (result.copy_abs() > Decimal('1e18') or (result != ZERO and result.copy_abs() < Decimal('1e-18'))):
        raise InvalidInput(f'{field}: fuera del rango numérico del MVP')
    if not result.is_finite():
        raise InvalidInput(f'{field}: número finito requerido')
    if positive and result <= ZERO:
        raise InvalidInput(f'{field}: debe ser positivo')
    if nonnegative and result < ZERO:
        raise InvalidInput(f'{field}: no puede ser negativo')
    return result


def _integer(value, field):
    result = _number(value, field, nonnegative=True)
    if result != result.to_integral_value():
        raise InvalidInput(f'{field}: entero requerido')
    return int(result)


def _timestamp(value, field):
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError):
        raise InvalidInput(f'{field}: fecha ISO con zona horaria requerida') from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise InvalidInput(f'{field}: zona horaria requerida')
    return result.astimezone(timezone.utc)


def _required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput(f'{field}: evidencia requerida')
    return value.strip()


def _fraction(value, field, *, positive=False):
    result = _number(value, field, positive=positive, nonnegative=True)
    if result >= ONE:
        raise InvalidInput(f'{field}: fracción debe ser menor que uno')
    return result


def _rejected(reasons, **metrics):
    result = dict(status='NO_OPERAR', reasons=reasons, quantity=0.0,
                  exposure_clp=0.0, risk_clp=0.0, reward_clp=0.0,
                  net_reward_risk=None, costs_clp=0.0)
    result.update(metrics)
    result['metrics'] = dict(metrics)
    return result


def evaluate_risk(policy, account, opportunity, now):
    """Fail closed on incomplete evidence; return JSON-serializable decision."""
    try:
        return _evaluate(policy, account, opportunity, now)
    except InvalidInput as error:
        return _rejected([str(error)])
    except DecimalException:
        return _rejected(['Precisión o aritmética fuera del rango admitido'])
    except (KeyError, TypeError, AttributeError):
        return _rejected(['Configuración o evidencia incompleta'])


def _evaluate(policy, account, opportunity, now):
    if not all(isinstance(item, dict) for item in (policy, account, opportunity)):
        raise InvalidInput('Política, cuenta y oportunidad deben ser objetos')
    now_utc = _timestamp(now, 'now')
    if policy.get('status') != 'approved_paper':
        return _rejected(['Política pendiente de aprobación humana para simulación'])
    execution = policy['execution']
    if (execution.get('mode') != 'paper'
            or any(execution.get(key) is not False for key in (
                'automatic_real_orders', 'real_orders_supported', 'leverage_allowed',
                'short_selling_allowed', 'derivatives_allowed', 'leveraged_etfs_allowed'))
            or execution.get('settled_cash_required') is not True):
        return _rejected(['Solo simulación con efectivo liquidado, sin apalancamiento'])
    if account.get('strategy_approved') is not True:
        return _rejected(['Estrategia sin aprobación humana vigente'])
    members = policy.get('team_members')
    if not isinstance(members, list) or len(members) != 3:
        return _rejected(['Se requieren tres integrantes configurados'])
    member_ids = []
    for member in members:
        identity = member.get('id') if isinstance(member, dict) else member
        if isinstance(identity, bool) or not isinstance(identity, (str, int)) or not str(identity).strip():
            return _rejected(['Identidades de integrantes incompletas'])
        member_ids.append(str(identity).strip())
    if len(set(member_ids)) != 3:
        return _rejected(['Los tres integrantes deben ser distintos'])
    for field in ('data_provider', 'execution_provider'):
        _required_text(policy.get(field), field)
    capital = _number(policy.get('capital_initial_clp'), 'capital_initial_clp', positive=True)
    if capital >= Decimal('100000'):
        return _rejected(['Capital fuera del alcance inicial inferior a 100000 CLP'])
    if _number(account.get('capital_initial_clp'), 'account.capital_initial_clp', positive=True) != capital:
        return _rejected(['Capital de cuenta y política no coinciden'])
    if policy.get('risk_base', {}).get('method') != 'minimum_initial_capital_and_session_start_equity':
        return _rejected(['Método de base de riesgo incompatible con el motor'])
    if policy.get('risk_base', {}).get('external_cash_flows_allowed_during_validation') is not False:
        return _rejected(['El experimento requiere capital sin flujos externos'])
    _check_session(policy, now_utc)
    if opportunity.get('side') != 'buy' or opportunity.get('instrument_type') not in ('spot', 'stock', 'etf'):
        return _rejected(['Solo compras de instrumentos sin apalancamiento admitidos'])
    if opportunity.get('leveraged') is not False or opportunity.get('liquidity_verified') is not True:
        return _rejected(['Instrumento apalancado o liquidez sin verificar'])
    if opportunity.get('currency') not in ('CLP', 'USD'):
        return _rejected(['Moneda no soportada por el MVP'])
    quote_age = _number(policy['data_requirements'].get('maximum_quote_age_seconds'),
                        'maximum_quote_age_seconds', positive=True)
    _required_text(opportunity.get('source'), 'source')
    _required_text(opportunity.get('fx_source'), 'fx_source')
    market_at = _timestamp(opportunity.get('market_timestamp'), 'market_timestamp')
    received_at = _timestamp(opportunity.get('received_timestamp'), 'received_timestamp')
    fx_at = _timestamp(opportunity.get('fx_timestamp'), 'fx_timestamp')
    expires_at = _timestamp(opportunity.get('expires_at'), 'expires_at')
    if received_at < market_at or received_at > now_utc or fx_at > now_utc:
        return _rejected(['Tiempos de cotización o conversión inconsistentes'])
    if (Decimal(str((now_utc - market_at).total_seconds())) > quote_age
            or Decimal(str((now_utc - fx_at).total_seconds())) > quote_age
            or expires_at <= now_utc):
        return _rejected(['Cotización, conversión o propuesta vencida'])
    cost_model = policy['execution_cost_model']
    cost_source = _required_text(cost_model.get('cost_schedule_source'), 'cost_schedule_source')
    cost_verified = _timestamp(cost_model.get('cost_schedule_verified_at_utc'), 'cost_schedule_verified_at_utc')
    if (cost_source != _required_text(opportunity.get('cost_source'), 'cost_source')
            or cost_verified != _timestamp(opportunity.get('cost_verified_at'), 'cost_verified_at')
            or cost_verified > now_utc):
        return _rejected(['Perfil de costes no coincide con la configuración verificada'])
    cost_age = _number(cost_model.get('maximum_cost_age_seconds'), 'maximum_cost_age_seconds', positive=True)
    if Decimal(str((now_utc - cost_verified).total_seconds())) > cost_age:
        return _rejected(['Tarifas vencidas: verificar perfil de costes'])
    _required_text(opportunity.get('coverage'), 'coverage')
    prices = {name: _number(opportunity.get(name), name, positive=True)
              for name in ('bid', 'ask', 'stop', 'target')}
    bid, ask, stop, target = (prices[key] for key in ('bid', 'ask', 'stop', 'target'))
    if not ZERO < stop < bid <= ask < target:
        return _rejected(['Precios inconsistentes para una compra: stop < bid <= ask < objetivo'])
    step = _number(opportunity.get('quantity_step'), 'quantity_step', positive=True)
    minimum = _number(opportunity.get('min_quantity'), 'min_quantity', positive=True)
    min_notional = _number(opportunity.get('min_notional'), 'min_notional', nonnegative=True)
    commission = _fraction(opportunity.get('commission_rate'), 'commission_rate')
    minimum_fee = _number(opportunity.get('min_fee'), 'min_fee', nonnegative=True)
    slippage = _fraction(opportunity.get('slippage_fraction'), 'slippage_fraction')
    fx = _number(opportunity.get('fx_rate'), 'fx_rate', positive=True)
    fx_fee = _fraction(opportunity.get('fx_cost_fraction'), 'fx_cost_fraction')
    if opportunity['currency'] == 'CLP' and fx != ONE:
        return _rejected(['Conversión CLP debe ser uno'])
    values = {key: _number(account.get(key), key, nonnegative=True) for key in (
        'cash_clp', 'open_exposure_clp', 'open_risk_clp', 'day_loss_clp')}
    equity = _number(account.get('equity_clp'), 'equity_clp', positive=True)
    start = _number(account.get('session_start_equity_clp'), 'session_start_equity_clp', positive=True)
    high_water = _number(account.get('high_water_clp'), 'high_water_clp', positive=True)
    if high_water < max(capital, start, equity):
        return _rejected(['Máximo patrimonial inconsistente'])
    base = min(capital, start)
    limits = policy['risk_limits_proposed']
    fractions = {key: _fraction(limits.get(key), key, positive=True) for key in (
        'per_trade_loss_fraction_including_execution_costs', 'per_trade_exposure_fraction',
        'total_exposure_fraction', 'total_open_risk_fraction', 'daily_loss_fraction',
        'maximum_drawdown_fraction', 'maximum_loss_from_initial_capital_fraction',
        'maximum_round_trip_cost_fraction_of_trade_risk_budget')}
    max_positions = _integer(limits.get('maximum_simultaneous_positions'), 'maximum_simultaneous_positions')
    max_entries = _integer(limits.get('maximum_entries_per_session'), 'maximum_entries_per_session')
    entries = _integer(account.get('entries_today'), 'entries_today')
    positions = _integer(account.get('open_positions'), 'open_positions')
    if max_positions < 1 or max_entries < 1 or positions >= max_positions or entries >= max_entries:
        return _rejected(['Límite de posiciones o entradas alcanzado'])
    day_loss = max(values['day_loss_clp'], start - equity, ZERO)
    daily_budget = base * fractions['daily_loss_fraction']
    initial_loss = max(capital - equity, ZERO)
    drawdown = high_water - equity
    if (day_loss >= daily_budget
            or initial_loss >= capital * fractions['maximum_loss_from_initial_capital_fraction']
            or drawdown >= high_water * fractions['maximum_drawdown_fraction']):
        return _rejected(['Límite de pérdida alcanzado; requiere revisión humana'])
    trade_budget = base * fractions['per_trade_loss_fraction_including_execution_costs']
    available_risk = min(
        trade_budget,
        base * fractions['total_open_risk_fraction'] - values['open_risk_clp'],
        daily_budget - day_loss - values['open_risk_clp'],
        capital * fractions['maximum_loss_from_initial_capital_fraction'] - initial_loss - values['open_risk_clp'],
        high_water * fractions['maximum_drawdown_fraction'] - drawdown - values['open_risk_clp'],
    )
    available_exposure = min(base * fractions['per_trade_exposure_fraction'],
                             base * fractions['total_exposure_fraction'] - values['open_exposure_clp'])
    cost_budget = trade_budget * fractions['maximum_round_trip_cost_fraction_of_trade_risk_budget']
    buy = ask * (ONE + slippage)
    stop_sale = stop * (ONE - slippage)
    target_sale = target * (ONE - slippage)

    def amounts(quantity):
        entry_fee = max(quantity * buy * commission, minimum_fee)
        entry_fx = quantity * buy * fx_fee
        exposure = quantity * buy * fx
        entry_cash = exposure + (entry_fee + entry_fx) * fx
        def exit_cost(price, executed):
            exit_fee = max(quantity * executed * commission, minimum_fee)
            return (quantity * ((buy - ask) + (price - executed)) + entry_fee
                    + exit_fee + entry_fx + quantity * executed * fx_fee) * fx
        stop_cost = exit_cost(stop, stop_sale)
        target_cost = exit_cost(target, target_sale)
        return dict(exposure=exposure, cash=entry_cash,
                    risk=quantity * (ask - stop) * fx + stop_cost,
                    reward=quantity * (target - ask) * fx - target_cost,
                    costs=max(stop_cost, target_cost), stop_cost=stop_cost,
                    target_cost=target_cost)

    def within_budget(calculation):
        return (calculation['risk'] <= available_risk
                and calculation['exposure'] <= available_exposure
                and calculation['cash'] <= values['cash_clp']
                and calculation['costs'] <= cost_budget)

    if available_risk <= ZERO or available_exposure <= ZERO or values['cash_clp'] <= ZERO:
        return _rejected(['Sin presupuesto de riesgo, exposición o efectivo liquidado'])
    upper = min(available_exposure / (buy * fx), values['cash_clp'] / (buy * fx),
                available_risk / ((ask - stop) * fx))
    max_units = int((upper / step).to_integral_value(rounding=ROUND_FLOOR))
    min_units = max(1, int((minimum / step).to_integral_value(rounding=ROUND_CEILING)),
                    int((min_notional / buy / step).to_integral_value(rounding=ROUND_CEILING)))
    if max_units < min_units:
        return _rejected(['Mínimo o precisión del instrumento incompatibles con los límites'])
    if opportunity.get('quantity') is not None:
        quantity = _number(opportunity['quantity'], 'quantity', positive=True)
        if quantity % step != ZERO or quantity < step * min_units or quantity > step * max_units:
            return _rejected(['Cantidad solicitada fuera de precisión, mínimos o límites'])
        calculation = amounts(quantity)
    else:
        # Monotone budgets: binary search avoids loops over tiny quantity steps.
        low, high = min_units, max_units
        feasible = 0
        while low <= high:
            middle = (low + high) // 2
            if within_budget(amounts(step * middle)):
                feasible, low = middle, middle + 1
            else:
                high = middle - 1
        if not feasible:
            return _rejected(['Costes, mínimo o efectivo hacen inviable cualquier cantidad'])
        quantity = step * feasible
        calculation = amounts(quantity)
    ratio = calculation['reward'] / calculation['risk']
    required_ratio = _number(limits.get('minimum_net_reward_to_risk_ratio'),
                             'minimum_net_reward_to_risk_ratio', positive=True)
    metrics = dict(quantity=float(quantity), exposure_clp=float(calculation['exposure']),
                   risk_clp=float(calculation['risk']), reward_clp=float(calculation['reward']),
                   net_reward_risk=float(ratio), costs_clp=float(calculation['costs']),
                   entry_cash_clp=float(calculation['cash']),
                   stop_costs_clp=float(calculation['stop_cost']),
                   target_costs_clp=float(calculation['target_cost']))
    if not within_budget(calculation):
        return _rejected(['Cantidad solicitada supera presupuesto con costes incluidos'], **metrics)
    if ratio < required_ratio:
        return _rejected(['Relación riesgo-beneficio neta insuficiente'], **metrics)
    return dict(status='APTO_PARA_SIMULAR', reasons=['Cumple límites calculados para simulación'], metrics=dict(metrics), **metrics)


def _check_session(policy, now):
    try:
        zone = ZoneInfo(_required_text(policy.get('session_timezone'), 'session_timezone'))
        start = time.fromisoformat(policy['session_start_local'])
        end = time.fromisoformat(policy['session_end_local'])
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        raise InvalidInput('Sesión o zona horaria sin configurar') from None
    if start.tzinfo or end.tzinfo or start == end:
        raise InvalidInput('Horario local de sesión inválido')
    local = now.astimezone(zone).time().replace(tzinfo=None)
    in_session = start <= local < end if start < end else local >= start or local < end
    if not in_session:
        raise InvalidInput('Fuera del horario de simulación aprobado')



