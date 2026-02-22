"""
Processing widgets for optothermal_processing integration.

This module provides GUI widgets for running data processing operations
from the optothermal_processing package within the laser_setup GUI.

Widgets:
- BaseProcessingWidget: Base class with Worker pattern and progress tracking
- PipelineWidget: Run staging, history building, and metrics extraction
- HistoryBrowserWidget: Browse and filter chip experiment histories
- PlotBuilderWidget: Configure and generate plots
- BatchPlotWidget: Run batch plots from YAML configuration
- CacheStatsWidget: View and manage cache statistics
"""

from .base_widget import BaseProcessingWidget, ProcessingWorker
from .pipeline_widget import PipelineWidget
from .history_browser_widget import HistoryBrowserWidget, PolarsTableModel
from .plot_builder_widget import PlotBuilderWidget
from .batch_plot_widget import BatchPlotWidget
from .cache_stats_widget import CacheStatsWidget

__all__ = [
    'BaseProcessingWidget',
    'ProcessingWorker',
    'PipelineWidget',
    'HistoryBrowserWidget',
    'PolarsTableModel',
    'PlotBuilderWidget',
    'BatchPlotWidget',
    'CacheStatsWidget',
]
