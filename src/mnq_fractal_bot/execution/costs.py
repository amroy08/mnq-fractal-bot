from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionCostConfig:
    """
    Cost assumptions for one futures contract.

    commission_round_trip:
        Total dollar fees for one completed
        entry + exit.

    slippage_ticks_entry:
        Number of ticks of adverse slippage
        assumed when entering.

    slippage_ticks_exit:
        Number of ticks of adverse slippage
        assumed when exiting.

    tick_size:
        MNQ minimum tick = 0.25 points.

    point_value:
        MNQ = $2 per index point.
    """

    commission_round_trip: float = 0.0

    slippage_ticks_entry: int = 0
    slippage_ticks_exit: int = 0

    tick_size: float = 0.25
    point_value: float = 2.0

    def __post_init__(self):
        if self.commission_round_trip < 0:
            raise ValueError(
                "commission_round_trip "
                "cannot be negative."
            )

        if self.slippage_ticks_entry < 0:
            raise ValueError(
                "slippage_ticks_entry "
                "cannot be negative."
            )

        if self.slippage_ticks_exit < 0:
            raise ValueError(
                "slippage_ticks_exit "
                "cannot be negative."
            )

        if self.tick_size <= 0:
            raise ValueError(
                "tick_size must be "
                "greater than zero."
            )

        if self.point_value <= 0:
            raise ValueError(
                "point_value must be "
                "greater than zero."
            )


@dataclass(frozen=True)
class TradeCostResult:
    gross_pnl: float

    commission_cost: float
    entry_slippage_cost: float
    exit_slippage_cost: float

    total_cost: float

    net_pnl: float


def calculate_trade_costs(
    gross_pnl: float,
    config: ExecutionCostConfig,
    quantity: int = 1,
) -> TradeCostResult:
    """
    Convert gross trade P&L into estimated
    net P&L after fees and slippage.

    This is intentionally independent from
    the Fractal strategy.

    The strategy determines whether a trade
    exists. This module only estimates the
    execution cost of that completed trade.
    """

    if quantity <= 0:
        raise ValueError(
            "quantity must be "
            "greater than zero."
        )

    # --------------------------------------------------
    # COMMISSION / FEES
    # --------------------------------------------------

    commission_cost = (
        config.commission_round_trip
        * quantity
    )

    # --------------------------------------------------
    # VALUE OF ONE TICK
    #
    # MNQ example:
    #
    # 0.25 points × $2 / point
    # = $0.50 per tick
    # --------------------------------------------------

    tick_value = (
        config.tick_size
        * config.point_value
    )

    # --------------------------------------------------
    # ENTRY SLIPPAGE
    # --------------------------------------------------

    entry_slippage_cost = (
        config.slippage_ticks_entry
        * tick_value
        * quantity
    )

    # --------------------------------------------------
    # EXIT SLIPPAGE
    # --------------------------------------------------

    exit_slippage_cost = (
        config.slippage_ticks_exit
        * tick_value
        * quantity
    )

    # --------------------------------------------------
    # TOTAL EXECUTION COST
    # --------------------------------------------------

    total_cost = (
        commission_cost
        + entry_slippage_cost
        + exit_slippage_cost
    )

    # --------------------------------------------------
    # NET P&L
    # --------------------------------------------------

    net_pnl = (
        gross_pnl
        - total_cost
    )

    return TradeCostResult(
        gross_pnl=gross_pnl,

        commission_cost=(
            commission_cost
        ),

        entry_slippage_cost=(
            entry_slippage_cost
        ),

        exit_slippage_cost=(
            exit_slippage_cost
        ),

        total_cost=(
            total_cost
        ),

        net_pnl=(
            net_pnl
        ),
    )