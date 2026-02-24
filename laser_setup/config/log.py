"""Logging configuration for the laser_setup package.
"""
import logging
import logging.config
import logging.handlers
import os
from collections.abc import Mapping
from contextvars import ContextVar
from pathlib import Path
from typing import Any


class Colors:
    RESET = "\033[0m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class ColoredFormatter(logging.Formatter):
    """Logging formatter with colored level names."""

    COLORS = {
        logging.DEBUG: Colors.BLUE,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }
    NAME_COLOR = Colors.CYAN

    def format(self, record):
        """Format the log record with colored level name.

        :param record: Log record to format
        :return: Formatted log message with colored level name
        """
        levelname = record.levelname
        if record.levelno in self.COLORS:
            color = self.COLORS[record.levelno]
            record.levelname = f"{color}{levelname}{Colors.RESET}"

        name = record.name
        if self.NAME_COLOR:
            record.name = f"{self.NAME_COLOR}{record.name}{Colors.RESET}"

        result = super().format(record)
        record.levelname = levelname
        record.name = name
        return result


_experiment_ctx: ContextVar[dict] = ContextVar(
    'experiment_ctx',
    default={'chip': '-', 'sample': '-', 'experiment': '-'}
)


class ExperimentContextFilter(logging.Filter):
    """Injects experiment context into every log record.

    Reads from a ContextVar so it is thread-safe and supports concurrent
    experiment runs. Fields added: chip, sample, experiment.
    If a record already carries those fields (e.g. from a LoggerAdapter),
    they are preserved.
    """
    _DEFAULTS = {'chip': '-', 'sample': '-', 'experiment': '-'}

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = _experiment_ctx.get()
        for key, default in self._DEFAULTS.items():
            if not hasattr(record, key):
                setattr(record, key, ctx.get(key, default))
        return True


def set_experiment_context(
    chip: str = '-',
    sample: str = '-',
    experiment: str = '-',
) -> None:
    """Set experiment context for the current execution context.

    Call once at the start of a procedure run. All subsequent log records
    from any logger in this context will carry chip/sample/experiment.

    :param chip: Chip group identifier
    :param sample: Sample identifier
    :param experiment: Procedure/experiment name
    """
    _experiment_ctx.set({'chip': chip, 'sample': sample, 'experiment': experiment})


def get_experiment_logger(
    chip: str,
    sample: str,
    experiment: str,
    logger_name: str = 'laser_setup',
) -> logging.LoggerAdapter:
    """Return a LoggerAdapter pre-loaded with experiment context.

    Also sets the ContextVar so bare module-level loggers in the same
    context carry the same fields.

    :param chip: Chip group identifier
    :param sample: Sample identifier
    :param experiment: Procedure/experiment name
    :param logger_name: Base logger to wrap (default: 'laser_setup')
    :return: LoggerAdapter with chip/sample/experiment in extra dict
    """
    set_experiment_context(chip=chip, sample=sample, experiment=experiment)
    return logging.LoggerAdapter(
        logging.getLogger(logger_name),
        {'chip': chip, 'sample': sample, 'experiment': experiment},
    )


def setup_logging(config: Mapping[str, Any]) -> None:
    """Set up logging from configuration dictionary.

    :param config: Dictionary containing logging configuration.
        Applies the config to `logging.config.dictConfig`.
        Also reads LOG_LEVEL environment variable to override the root and
        laser_setup logger levels at runtime.
    """
    filename = config.get('handlers', {}).get('file', {}).get('filename')
    if filename:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(config=config)

    # Optional runtime level override via environment variable
    level_env = os.environ.get('LOG_LEVEL', '').upper()
    if level_env:
        numeric = getattr(logging, level_env, None)
        if not isinstance(numeric, int):
            logging.getLogger('laser_setup').warning(
                "Invalid LOG_LEVEL=%r; ignoring. Valid values: DEBUG INFO WARNING ERROR CRITICAL",
                level_env,
            )
        else:
            logging.getLogger().setLevel(numeric)
            logging.getLogger('laser_setup').setLevel(numeric)

    # Attach ExperimentContextFilter to all handlers so %(chip)s etc. always resolve
    ctx_filter = ExperimentContextFilter()
    for handler in logging.root.handlers:
        handler.addFilter(ctx_filter)
    for name in ('laser_setup',):
        for handler in logging.getLogger(name).handlers:
            handler.addFilter(ctx_filter)


default_log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            '()': '${class:laser_setup.config.log.ColoredFormatter}',
            'format': '%(asctime)s [%(levelname)s] %(message)s (%(name)s)',
            'datefmt': '%H:%M:%S',
        },
        'file': {
            'format': (
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ' [chip=%(chip)s sample=%(sample)s exp=%(experiment)s]'
            ),
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'console',
        },
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'file',
            'filename': 'log/laser_setup.log',
            'when': 'midnight',
            'backupCount': 14,
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'root': {
            'level': 'INFO',
            'handlers': ['file'],
        },
        'laser_setup': {
            'level': 'INFO',
            'handlers': ['console'],
        },
        'laser_setup.display.widgets.log_widget': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
        'pymeasure.log': {
            'level': 'INFO',
            'handlers': ['file'],
        },
    },
}
