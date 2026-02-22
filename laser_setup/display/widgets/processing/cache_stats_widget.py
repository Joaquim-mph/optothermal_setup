"""
Cache statistics widget for monitoring and managing the data cache.

Provides a GUI for viewing cache statistics (hit rate, memory usage)
and clearing the cache.
"""

import logging
from typing import Optional

from qtpy import QtCore, QtWidgets

from .base_widget import BaseProcessingWidget

log = logging.getLogger(__name__)


class CacheStatsWidget(BaseProcessingWidget):
    """
    Widget for viewing and managing cache statistics.

    Features:
    - Display cache size, hits, misses, hit rate
    - Show memory usage
    - Refresh and clear buttons
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self._refresh_stats()

    def _setup_ui(self):
        """Create the user interface."""
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel("Cache Statistics")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Stats display group
        stats_group = QtWidgets.QGroupBox("Statistics")
        stats_layout = QtWidgets.QGridLayout(stats_group)

        # Row 0: Items
        stats_layout.addWidget(QtWidgets.QLabel("Cached Items:"), 0, 0)
        self.label_items = QtWidgets.QLabel("0")
        self.label_items.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self.label_items, 0, 1)

        # Row 1: Memory
        stats_layout.addWidget(QtWidgets.QLabel("Memory Usage:"), 1, 0)
        self.label_memory = QtWidgets.QLabel("0 MB")
        self.label_memory.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self.label_memory, 1, 1)

        # Row 2: Max memory
        stats_layout.addWidget(QtWidgets.QLabel("Max Memory:"), 2, 0)
        self.label_max_memory = QtWidgets.QLabel("500 MB")
        stats_layout.addWidget(self.label_max_memory, 2, 1)

        # Row 3: Utilization
        stats_layout.addWidget(QtWidgets.QLabel("Utilization:"), 3, 0)
        self.progress_utilization = QtWidgets.QProgressBar()
        self.progress_utilization.setRange(0, 100)
        self.progress_utilization.setValue(0)
        stats_layout.addWidget(self.progress_utilization, 3, 1)

        layout.addWidget(stats_group)

        # Hit/miss stats group
        perf_group = QtWidgets.QGroupBox("Performance")
        perf_layout = QtWidgets.QGridLayout(perf_group)

        # Row 0: Hits
        perf_layout.addWidget(QtWidgets.QLabel("Cache Hits:"), 0, 0)
        self.label_hits = QtWidgets.QLabel("0")
        self.label_hits.setStyleSheet("color: green; font-weight: bold;")
        perf_layout.addWidget(self.label_hits, 0, 1)

        # Row 1: Misses
        perf_layout.addWidget(QtWidgets.QLabel("Cache Misses:"), 1, 0)
        self.label_misses = QtWidgets.QLabel("0")
        self.label_misses.setStyleSheet("color: orange; font-weight: bold;")
        perf_layout.addWidget(self.label_misses, 1, 1)

        # Row 2: Hit rate
        perf_layout.addWidget(QtWidgets.QLabel("Hit Rate:"), 2, 0)
        self.label_hit_rate = QtWidgets.QLabel("0%")
        self.label_hit_rate.setStyleSheet("font-weight: bold; font-size: 14px;")
        perf_layout.addWidget(self.label_hit_rate, 2, 1)

        # Row 3: Evictions
        perf_layout.addWidget(QtWidgets.QLabel("Evictions:"), 3, 0)
        self.label_evictions = QtWidgets.QLabel("0")
        perf_layout.addWidget(self.label_evictions, 3, 1)

        # Row 4: Invalidations
        perf_layout.addWidget(QtWidgets.QLabel("Invalidations:"), 4, 0)
        self.label_invalidations = QtWidgets.QLabel("0")
        perf_layout.addWidget(self.label_invalidations, 4, 1)

        layout.addWidget(perf_group)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()

        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.setMinimumWidth(100)
        button_layout.addWidget(self.btn_refresh)

        self.btn_clear = QtWidgets.QPushButton("Clear Cache")
        self.btn_clear.setMinimumWidth(100)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        button_layout.addWidget(self.btn_clear)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Auto-refresh checkbox
        self.check_auto_refresh = QtWidgets.QCheckBox("Auto-refresh every 5 seconds")
        layout.addWidget(self.check_auto_refresh)

        # Timer for auto-refresh
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setInterval(5000)
        self._refresh_timer.timeout.connect(self._refresh_stats)

        # Spacer
        layout.addStretch()

    def _connect_signals(self):
        """Connect signals to slots."""
        self.btn_refresh.clicked.connect(self._refresh_stats)
        self.btn_clear.clicked.connect(self._clear_cache)
        self.check_auto_refresh.toggled.connect(self._toggle_auto_refresh)

    def _toggle_auto_refresh(self, enabled: bool):
        """Toggle auto-refresh timer."""
        if enabled:
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()

    def _refresh_stats(self):
        """Refresh cache statistics display."""
        try:
            from src.cli.cache import get_cache

            cache = get_cache()
            info = cache.get_info()
            stats = cache.get_stats()

            # Update labels
            self.label_items.setText(str(info.get("item_count", 0)))

            memory_mb = info.get("total_size_mb", 0)
            self.label_memory.setText(f"{memory_mb:.2f} MB")

            max_memory = info.get("max_size_mb", 500)
            self.label_max_memory.setText(f"{max_memory:.0f} MB")

            utilization = info.get("utilization", 0) * 100
            self.progress_utilization.setValue(int(utilization))

            # Update performance stats
            self.label_hits.setText(str(stats.hits))
            self.label_misses.setText(str(stats.misses))
            self.label_evictions.setText(str(stats.evictions))
            self.label_invalidations.setText(str(stats.invalidations))

            hit_rate = stats.hit_rate() * 100
            self.label_hit_rate.setText(f"{hit_rate:.1f}%")

            # Color hit rate based on value
            if hit_rate >= 80:
                self.label_hit_rate.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            elif hit_rate >= 50:
                self.label_hit_rate.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
            else:
                self.label_hit_rate.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")

        except ImportError:
            self._show_unavailable()
        except Exception as e:
            log.exception("Failed to refresh cache stats")
            self.label_items.setText("Error")
            self.label_memory.setText(str(e)[:20])

    def _show_unavailable(self):
        """Show that cache is unavailable."""
        self.label_items.setText("N/A")
        self.label_memory.setText("N/A")
        self.label_hits.setText("N/A")
        self.label_misses.setText("N/A")
        self.label_hit_rate.setText("N/A")
        self.label_evictions.setText("N/A")
        self.label_invalidations.setText("N/A")
        self.progress_utilization.setValue(0)

    def _clear_cache(self):
        """Clear the cache."""
        if not self.ask_confirmation("Are you sure you want to clear the cache?"):
            return

        try:
            from src.cli.cache import clear_cache

            clear_cache()
            self._refresh_stats()
            self.show_success("Cache cleared successfully!")

        except ImportError:
            self.show_error("Cache module not available")
        except Exception as e:
            self.show_error(f"Failed to clear cache: {e}")

    def closeEvent(self, event):
        """Stop timer when closing."""
        self._refresh_timer.stop()
        super().closeEvent(event)
