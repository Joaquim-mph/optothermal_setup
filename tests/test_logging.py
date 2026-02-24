#!/usr/bin/env python3
"""Smoke-test for the laser_setup logging improvements.

Run with:
    python tools/test_logging.py
    LOG_LEVEL=DEBUG python tools/test_logging.py
"""
import copy
import logging
import os
import tempfile

# ---------------------------------------------------------------------------
# 1. Setup — patch log path to a temp dir, then call setup_logging
# ---------------------------------------------------------------------------
from laser_setup.config.log import (
    default_log_config,
    get_experiment_logger,
    set_experiment_context,
    setup_logging,
)

tmpdir = tempfile.mkdtemp(prefix='laser_setup_log_test_')
log_file = os.path.join(tmpdir, 'laser_setup.log')

test_config = copy.deepcopy(default_log_config)
test_config['handlers']['file']['filename'] = log_file
# Remove the OmegaConf resolver placeholder so dictConfig works standalone
test_config['formatters']['console']['()'] = 'laser_setup.config.log.ColoredFormatter'

setup_logging(test_config)

print(f"[1] setup_logging() completed. Log file: {log_file}")


# ---------------------------------------------------------------------------
# 2. Rotation — verify TimedRotatingFileHandler is active
# ---------------------------------------------------------------------------
file_logger = logging.getLogger()
rotating_handlers = [
    h for h in file_logger.handlers
    if isinstance(h, logging.handlers.TimedRotatingFileHandler)
]
assert rotating_handlers, "Expected TimedRotatingFileHandler on root logger"
print("[2] TimedRotatingFileHandler is active — rotation OK")


# ---------------------------------------------------------------------------
# 3. Context adapter — verify chip/sample/experiment appear in file log
# ---------------------------------------------------------------------------
adapter = get_experiment_logger(chip='TestChip', sample='A', experiment='SmokeTest')
adapter.info("Context adapter test message")

# Flush handlers
for h in logging.root.handlers:
    h.flush()

with open(log_file) as f:
    content = f.read()

assert '[chip=TestChip sample=A exp=SmokeTest]' in content, (
    f"Context fields not found in log file.\nLog content:\n{content}"
)
print("[3] Experiment context fields appear in file log — context adapter OK")


# ---------------------------------------------------------------------------
# 4. Traceback capture — verify exc_info appears in file log
# ---------------------------------------------------------------------------
try:
    raise ValueError("deliberate test error")
except Exception:
    logging.getLogger('laser_setup').error("Caught deliberate error", exc_info=True)

for h in logging.root.handlers:
    h.flush()

with open(log_file) as f:
    content = f.read()

assert 'Traceback' in content, (
    f"Expected 'Traceback' in log file after exc_info=True.\nLog content:\n{content}"
)
print("[4] Traceback captured in file log — exc_info OK")


# ---------------------------------------------------------------------------
# 5. ENV override — set LOG_LEVEL=DEBUG, re-run setup_logging, check level
# ---------------------------------------------------------------------------
os.environ['LOG_LEVEL'] = 'DEBUG'
setup_logging(test_config)
assert logging.getLogger().level == logging.DEBUG, (
    f"Root logger level should be DEBUG, got {logging.getLevelName(logging.getLogger().level)}"
)
assert logging.getLogger('laser_setup').level == logging.DEBUG, (
    f"laser_setup logger level should be DEBUG"
)
os.environ.pop('LOG_LEVEL')
print("[5] LOG_LEVEL=DEBUG env override works — ENV override OK")


# ---------------------------------------------------------------------------
# 6. GUI handler isolation — named logger does not capture third-party noise
# ---------------------------------------------------------------------------
# Simulate what ExperimentWindow does
laser_setup_logger = logging.getLogger("laser_setup")
captured = []

class _CapturingHandler(logging.Handler):
    def emit(self, record):
        captured.append(record.name)

cap = _CapturingHandler()
laser_setup_logger.addHandler(cap)

logging.getLogger("some_third_party").warning("third-party noise")
logging.getLogger("laser_setup.test_isolation").info("project message")

laser_setup_logger.removeHandler(cap)

assert 'some_third_party' not in captured, (
    f"Third-party logger message leaked into laser_setup logger: {captured}"
)
assert any('laser_setup' in n for n in captured), (
    f"laser_setup message not captured: {captured}"
)
print("[6] Named logger isolates third-party noise — GUI handler isolation OK")


# ---------------------------------------------------------------------------
# All checks passed
# ---------------------------------------------------------------------------
print(f"\nAll checks passed. Log file written to: {log_file}")
