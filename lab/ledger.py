"""Pure paper-ledger metrics; no storage, uploads, accounts or orders.

Each closed trade requires mode='paper', aware ISO closed_at, pnl_clp
ALREADY net of execution costs and before taxes, and costs_clp >= 0.
Optional id must be unique. Costs are reported, never subtracted a second time.
Rows are sorted chronologically. Only paper rows are accepted: mixed real data
is rejected rather than silently included. Missing capital leaves returns and
cash-based metrics unavailable; zero is not substituted for unknown capital.

Optional equity_curve is an ordered list of CLP numbers or objects with
'equity_clp', 'timestamp' (aware ISO) and optional mode='paper'. It includes liquidation
costs and open positions when supplied by the caller. Without it drawdown is
only measured at closed-trade boundaries, explicitly labeled as incomplete.
"""
from decimal import Decimal, DecimalException
from .risk import InvalidInput, _number, _timestamp


def summarize_ledger(trades, initial_capital_clp, equity_curve=None):
    try:
        return _summarize(trades, initial_capital_clp, equity_curve)
    except DecimalException:
        raise ValueError('Precisión o aritmética fuera del rango admitido') from None


def _summarize(trades, initial_capital_clp, equity_curve=None):
    if not isinstance(trades, list):
        raise ValueError('El historial debe ser una lista de operaciones simuladas')
    rows, identifiers = [], set()
    try:
        for trade in trades:
            if not isinstance(trade, dict) or trade.get('mode') != 'paper':
                raise ValueError('Solo se admiten registros de simulación separados')
            identifier = trade.get('id')
            if identifier is not None:
                if not isinstance(identifier, (str, int)) or isinstance(identifier, bool):
                    raise ValueError('Identificador de operación inválido')
                if str(identifier) in identifiers:
                    raise ValueError('Identificador de operación repetido')
                identifiers.add(str(identifier))
            rows.append((_timestamp(trade.get('closed_at'), 'closed_at'),
                         _number(trade.get('pnl_clp'), 'pnl_clp'),
                         _number(trade.get('costs_clp'), 'costs_clp', nonnegative=True)))
        rows.sort(key=lambda row: row[0])
        capital = None if initial_capital_clp is None else _number(
            initial_capital_clp, 'initial_capital_clp', positive=True)
        points = _curve_points(equity_curve) if equity_curve is not None else None
    except InvalidInput as error:
        raise ValueError(str(error)) from None
    count = len(rows)
    net = sum((row[1] for row in rows), Decimal('0'))
    costs = sum((row[2] for row in rows), Decimal('0'))
    wins = sum(row[1] > 0 for row in rows)
    losses = sum(row[1] < 0 for row in rows)
    positive = sum((row[1] for row in rows if row[1] > 0), Decimal('0'))
    negative = -sum((row[1] for row in rows if row[1] < 0), Decimal('0'))
    result = dict(
        status='DATOS_INSUFICIENTES' if capital is None else ('SIN_OPERACIONES' if not count else 'CALCULADO'),
        mode='paper', tax_basis='execution_net_before_taxes',
        closed_trades=count, winning_trades=wins, losing_trades=losses,
        breakeven_trades=count - wins - losses,
        net_pnl_clp=float(net), costs_clp=float(costs),
        win_rate=wins / count if count else None,
        average_pnl_clp=float(net / count) if count else None,
        profit_factor=float(positive / negative) if negative else None,
        initial_capital_clp=float(capital) if capital is not None else None,
        closed_equity_clp=float(capital + net) if capital is not None else None,
        equity_clp=None, return_fraction=None, max_drawdown_clp=None,
        max_drawdown_fraction=None,
        drawdown_basis='marked_equity' if points is not None else 'closed_trades_only',
        return_basis='marked_equity' if points is not None else 'closed_trades_only',
    )
    if capital is None:
        return result
    if points is None:
        running = capital
        points = []
        for _, pnl, _ in rows:
            running += pnl
            points.append(running)
    equity = points[-1] if points else capital
    peak, max_dd, max_dd_fraction = capital, Decimal('0'), Decimal('0')
    for value in points:
        peak = max(peak, value)
        drawdown = peak - value
        max_dd = max(max_dd, drawdown)
        max_dd_fraction = max(max_dd_fraction, drawdown / peak)
    result.update(equity_clp=float(equity), return_fraction=float((equity - capital) / capital),
                  max_drawdown_clp=float(max_dd), max_drawdown_fraction=float(max_dd_fraction))
    return result


def _curve_points(curve):
    if not isinstance(curve, list) or not curve:
        raise ValueError('La curva patrimonial debe contener puntos ordenados')
    points, previous, kind = [], None, isinstance(curve[0], dict)
    for point in curve:
        if isinstance(point, dict) != kind:
            raise ValueError('La curva patrimonial debe utilizar un solo formato')
        if isinstance(point, dict):
            if point.get('mode', 'paper') != 'paper':
                raise ValueError('La curva debe ser exclusivamente simulada')
            when = _timestamp(point.get('timestamp'), 'equity.timestamp')
            if previous is not None and when <= previous:
                raise ValueError('Las fechas patrimoniales deben ser crecientes')
            previous = when
            value = point.get('equity_clp')
        else:
            value = point
        points.append(_number(value, 'equity_clp'))
    return points


