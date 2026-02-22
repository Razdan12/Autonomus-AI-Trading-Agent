"""
AI Trading Agent — Main Orchestrator
Lead Trading Strategist focused on Crypto (Indodax).

Strategy:
- Analyze OHLCV data via ccxt + whale movement detection
- Confirm macro trend with whale accumulation before entry
- Ignore retail panic (follow smart money)
- Max 2% risk per position, mandatory stop loss
"""

import sys
import time
import signal
import argparse
import schedule
from datetime import datetime

from config import Config
from data.database import Database
from data.market_data import MarketDataFetcher
from data.volume_tracker import VolumeTracker
from analysis.technical import TechnicalAnalyzer
from analysis.volume_analyzer import VolumeAnalyzer
from analysis.signal_generator import SignalGenerator, TradingSignal
from trading.risk_manager import RiskManager
from trading.executor import OrderExecutor
from trading.position_tracker import PositionTracker
from utils.logger import setup_logging, get_logger
from utils.dashboard import Dashboard, print_startup_banner

logger = get_logger(__name__)


class TradingAgent:
    """
    Main AI Trading Agent orchestrator.
    
    Runs the analysis → signal → risk → execution pipeline
    on a configurable schedule (default: every 1 hour).
    """

    def __init__(self, config: Config):
        self.config = config
        self.running = False

        # Initialize all components
        self.db = Database()
        self.market_data = MarketDataFetcher(config)
        self.volume_tracker = VolumeTracker(config, self.market_data, self.db)
        self.tech_analyzer = TechnicalAnalyzer()
        self.volume_analyzer = VolumeAnalyzer(config, self.db)
        self.signal_generator = SignalGenerator()
        self.risk_manager = RiskManager(config, self.db)
        self.executor = OrderExecutor(config, self.market_data, self.db)
        self.position_tracker = PositionTracker(
            config, self.db, self.market_data,
            self.risk_manager, self.executor,
        )
        self.dashboard = Dashboard()

        # State
        self.last_signals = {}
        self.last_volume_data = {}

    def start(self):
        """Start the trading agent."""
        print_startup_banner(self.config)

        # Validate config
        issues = self.config.validate()
        for issue in issues:
            if issue.startswith("ERROR"):
                logger.error(issue)
                sys.exit(1)
            else:
                logger.warning(issue)

        # Validate trading pairs
        try:
            valid_pairs = self.market_data.validate_pairs(self.config.trading.pairs)
            if not valid_pairs:
                logger.error("❌ Tidak ada trading pairs yang valid!")
                sys.exit(1)
            self.config.trading.pairs = valid_pairs
            logger.info(f"✅ Trading pairs aktif: {valid_pairs}")
        except Exception as e:
            logger.warning(f"⚠️ Could not validate pairs: {e}")
            logger.info("Using configured pairs as-is")

        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        self.running = True
        logger.info("🚀 AI Trading Agent started!")

        # Run immediately on start
        self._run_cycle()

        # Schedule periodic runs
        interval = self.config.trading.analysis_interval_minutes
        schedule.every(interval).minutes.do(self._run_cycle)

        # Schedule position checks more frequently (every 5 min)
        schedule.every(5).minutes.do(self._check_positions)

        logger.info(
            f"📅 Scheduled: Analysis every {interval} min | "
            f"Position check every 5 min"
        )

        # Main loop
        while self.running:
            schedule.run_pending()
            time.sleep(10)

    def _run_cycle(self):
        """Run one complete analysis → signal → execution cycle."""
        cycle_start = datetime.utcnow()
        logger.info(f"\n{'═' * 60}")
        logger.info(f"🔄 Analysis Cycle Start: {cycle_start.isoformat()}")
        logger.info(f"{'═' * 60}")

        try:
            # ──── Step 1: Analyze Each Trading Pair ────
            for symbol in self.config.trading.pairs:
                try:
                    self._analyze_pair(symbol)
                except Exception as e:
                    logger.error(f"❌ Error analyzing {symbol}: {e}")

                time.sleep(2)  # Rate limit between pairs

            # ──── Step 3: Display Dashboard ────
            self._display_dashboard()

            duration = (datetime.utcnow() - cycle_start).total_seconds()
            logger.info(f"✅ Analysis cycle complete in {duration:.1f}s")

        except Exception as e:
            logger.error(f"❌ Fatal error in analysis cycle: {e}")

    def _analyze_pair(self, symbol: str):
        """Analyze a single trading pair and execute if signal is strong."""
        logger.info(f"\n{'─' * 40}")
        logger.info(f"📊 Analyzing: {symbol}")
        logger.info(f"{'─' * 40}")

        # ──── Fetch OHLCV Data ────
        try:
            ohlcv_data = self.market_data.fetch_multi_timeframe(
                symbol, ["1h", "4h"]
            )
        except Exception as e:
            logger.error(f"❌ Failed to fetch OHLCV for {symbol}: {e}")
            return

        # Save candles to database
        for tf, df in ohlcv_data.items():
            if not df.empty:
                candles = df.reset_index()[
                    ["timestamp", "open", "high", "low", "close", "volume"]
                ].values.tolist()
                self.db.save_candles(symbol, tf, candles)

        # ──── Technical Analysis (multi-timeframe) ────
        tech_signals = {}
        for tf, df in ohlcv_data.items():
            if not df.empty:
                tech = self.tech_analyzer.analyze(df, symbol, tf)
                if tech:
                    tech_signals[tf] = tech

        if not tech_signals:
            logger.warning(f"⚠️ No technical signals for {symbol}")
            return

        # ──── Volume & Imbalance Analysis ────
        # Scan for large trades and orderbook walls (saves to DB)
        self.volume_tracker.scan_anomalies(symbol)

        # Generate volume signal from recent DB events
        volume_signal = self.volume_analyzer.analyze(symbol)
        
        self.last_volume_data[symbol] = volume_signal.to_dict()

        # ──── Generate Combined Signal (Multi-TF) ────
        trading_signal = self.signal_generator.generate_multi_timeframe(
            tech_signals, volume_signal
        )

        # Save signal to database
        signal_dict = trading_signal.to_dict()
        signal_dict["symbol"] = symbol
        signal_dict["timeframe"] = self.config.trading.timeframe
        signal_id = self.db.save_signal(signal_dict)

        self.last_signals[symbol] = signal_dict

        logger.info(
            f"📡 {symbol} → {trading_signal.action} "
            f"(confidence: {trading_signal.confidence:.0%})"
        )
        logger.info(f"   Reason: {trading_signal.reason}")

        # ──── Execute Trading Decision ────
        self._execute_signal(symbol, trading_signal, tech_signals, signal_id)

    def _execute_signal(
        self,
        symbol: str,
        signal: TradingSignal,
        tech_signals: dict,
        signal_id: int,
    ):
        """Execute trading decision based on signal."""

        # Only act on BUY or SELL signals
        if signal.action in ("STRONG_BUY", "BUY"):
            side = "buy"
        elif signal.action in ("STRONG_SELL", "SELL"):
            side = "sell"
        else:
            logger.info(f"📊 {symbol}: HOLD — No action taken")
            return

        # Get current price and ATR
        try:
            ticker = self.market_data.fetch_ticker(symbol)
            entry_price = ticker["last"]
        except Exception as e:
            logger.error(f"❌ Cannot get price for {symbol}: {e}")
            return

        # Get ATR from primary timeframe
        primary_tf = list(tech_signals.keys())[0]
        atr = tech_signals[primary_tf].atr if primary_tf in tech_signals else 0

        if atr <= 0:
            logger.warning(f"⚠️ ATR is zero for {symbol} — cannot calculate stop loss")
            return

        # Get equity
        if self.config.trading.mode == "paper":
            equity = 300_000
        else:
            try:
                balance = self.market_data.fetch_balance()
                equity = balance.get("free", {}).get("IDR", 0)
            except Exception:
                equity = 0

        # Calculate order with risk management
        order_plan = self.risk_manager.calculate_order(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            atr=atr,
            equity=equity,
        )

        if not order_plan.approved:
            logger.warning(
                f"🚫 {symbol}: Order rejected — {order_plan.rejection_reason}"
            )
            return

        # Add signal reference
        trade_result = self.executor.execute(order_plan)

        if trade_result:
            # Update signal_id in trade
            cursor = self.db.conn.cursor()
            cursor.execute(
                "UPDATE trades SET signal_id = ? WHERE id = ?",
                (signal_id, trade_result["id"])
            )
            self.db.conn.commit()

            logger.trade(
                f"🎯 Trade executed for {symbol}: {side.upper()} | "
                f"Entry: {order_plan.entry_price:,.0f} | "
                f"SL: {order_plan.stop_loss:,.0f} | "
                f"TP: {order_plan.take_profit:,.0f} | "
                f"Risk: {order_plan.risk_amount:,.0f} IDR"
            )

    def _check_positions(self):
        """Check open positions for SL/TP hits."""
        try:
            actions = self.position_tracker.check_positions()
            if actions:
                for action in actions:
                    logger.trade(f"⚡ Position update: {action}")
        except Exception as e:
            logger.error(f"❌ Error checking positions: {e}")

    def _display_dashboard(self):
        """Display the CLI dashboard."""
        try:
            portfolio = self.position_tracker.get_portfolio_summary()
            self.dashboard.display(
                portfolio=portfolio,
                last_signals=self.last_signals,
                volume_summary=self.last_volume_data,
            )
        except Exception as e:
            logger.warning(f"⚠️ Dashboard display error: {e}")

    def _shutdown(self, signum, frame):
        """Graceful shutdown handler."""
        logger.info("\n🛑 Shutting down AI Trading Agent...")
        self.running = False
        self.db.close()
        logger.info("👋 Goodbye!")
        sys.exit(0)


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="🤖 AI Trading Agent — Indodax Platform"
    )
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default=None,
        help="Trading mode (overrides .env)"
    )
    parser.add_argument(
        "--pairs",
        type=str,
        default=None,
        help="Trading pairs, comma-separated (overrides .env)"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default=None,
        help="Primary timeframe (overrides .env)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Analysis interval in minutes (overrides .env)"
    )

    args = parser.parse_args()

    # Load config
    config = Config()

    # Apply CLI overrides
    if args.mode:
        config.trading.mode = args.mode
    if args.pairs:
        config.trading.pairs = [p.strip() for p in args.pairs.split(",")]
    if args.timeframe:
        config.trading.timeframe = args.timeframe
    if args.interval:
        config.trading.analysis_interval_minutes = args.interval

    # Setup logging
    setup_logging(config.log.level, config.log.directory)

    # Start agent
    agent = TradingAgent(config)
    agent.start()


if __name__ == "__main__":
    main()
