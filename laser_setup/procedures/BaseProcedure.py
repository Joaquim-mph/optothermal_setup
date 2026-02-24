import inspect
import logging
import time
from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from functools import wraps
from typing import Any

from pymeasure.experiment import (BooleanParameter, Metadata, Parameter,
                                  Procedure)

from ..config import configurable
from ..instruments import InstrumentManager, Keithley2450, TENMA

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


@configurable('procedures', on_definition=False)
class BaseProcedure(Procedure):
    """Base procedure for all measurements. It defines basic
    parameters that are present in all procedures. It also provides
    methods for connecting instruments and shutting down an experiment.
    You can override any of the attributes or methods in a subclass.

    :attr name: Name of the procedure,
    :attr instruments: InstrumentManager instance
    :attr procedure_version: Version of the procedure
    :attr show_more: Show more parameters
    :attr info: Information about the procedure
    :attr exec_startup: Execute startup
    :attr exec_shutdown: Execute shutdown
    :attr start_time: Start time of the procedure
    :attr time: Time module
    :attr INPUTS: List of input parameters to be displayed
    :attr EXCLUDE: List of parameters to exclude from the save file
    :attr DATA_COLUMNS: List of data columns
    :attr SEQUENCER_INPUTS: List of inputs for the sequencer
    """
    name: str = ""

    instruments = InstrumentManager()

    procedure_version = Parameter("Procedure version", default="1.0.0")
    show_more = BooleanParameter("Show more", default=False)
    info = Parameter("Information", default="None")

    # Startup and shutdown execution
    skip_startup = BooleanParameter("Skip startup", default=False, group_by='show_more')
    skip_shutdown = BooleanParameter("Skip shutdown", default=False, group_by='show_more')

    # Metadata
    start_time = Metadata("Start time", fget="time.time")
    # Access to time module as attribute for Metadata.fget
    time = time

    INPUTS: list[str] = ['show_more', 'skip_startup', 'skip_shutdown', 'info']
    EXCLUDE: list[str] = ['show_more', 'skip_startup', 'skip_shutdown']

    def connect_instruments(self):
        """Connects all queued instruments via the InstrumentManager,
        replacing the InstrumentProxy instances with actual instrument instances.
        This method is called even if skip_startup is set to True.

        Override this method to handle instrument connections differently.
        """
        self.instruments.connect_all(self)

    def patch_parameters(self) -> None:
        """Patch parameters to update their values. This method is called
        before the measurement starts. Override this method in a subclass.
        """
        pass

    def startup(self):
        """Startup method that handles the initialization of instruments and
        other components before the measurement starts. Override this method
        in a subclass.
        """
        params = {k: getattr(v, 'value', None) for k, v in self._parameters.items()}
        log.debug("Starting %s | params: %s", type(self).__name__, params)
        self.connect_instruments()

    def shutdown(self):
        """Shutdown method that handles the cleanup of instruments and other
        components after the measurement finishes. Override this method in a
        subclass.

        Note: Instruments are kept connected and cached for reuse between experiments.
        They will only be fully shut down when the application exits.
        """
        if self.should_stop():
            self._reset_instruments_on_abort()
        # Don't shut down instruments between experiments - keep them cached for reuse
        # This prevents USB "Resource busy" errors on consecutive experiments
        log.debug("Keeping instruments connected for reuse in next experiment")

    def _reset_instruments_on_abort(self) -> None:
        """Reset critical instrument outputs to safe values on abort."""
        for name, instrument in inspect.getmembers(self):
            if isinstance(instrument, TENMA):
                self._reset_tenma(instrument, name)
            elif isinstance(instrument, Keithley2450):
                self._reset_keithley(instrument, name)

    @staticmethod
    def _reset_tenma(tenma: TENMA, name: str) -> None:
        try:
            tenma.ramp_to_voltage(0., vg_step=0.5)
            tenma.output = False
            log.info(f"Reset TENMA '{name}' to 0 V and disabled output after abort.")
        except Exception:
            log.warning("Failed to reset TENMA '%s' after abort", name, exc_info=True)

    @staticmethod
    def _reset_keithley(meter: Keithley2450, name: str) -> None:
        try:
            meter.source_voltage = 0.
        except Exception:
            log.warning("Failed to set Keithley '%s' source to 0 V after abort", name,
                        exc_info=True)

        if hasattr(meter, "disable_source"):
            try:
                meter.disable_source()
                log.info(f"Disabled Keithley '{name}' source after abort.")
            except Exception:
                log.warning("Failed to disable Keithley '%s' source after abort", name,
                            exc_info=True)
        elif hasattr(meter, "source_enabled"):
            try:
                meter.source_enabled = False
                log.info(f"Disabled Keithley '{name}' source after abort.")
            except Exception:
                log.warning("Failed to disable Keithley '%s' source after abort", name,
                            exc_info=True)

    def __init__(self, parameters: Mapping[str, Any] | None = None, **kwargs):
        """Initialize a procedure instance. It wraps the startup
        and shutdown methods to skip execution if the corresponding Parameters are True.

        :param parameters: Dictionary with procedure-specific parameters to override
        :param kwargs: Dictionary with extra attributes to update in the instance
        """
        self.override_parameters(parameters or {})
        super().__init__(**kwargs)

        # Wrap methods to skip execution
        self.startup = self._wrap_skip(self.startup, 'skip_startup', self.connect_instruments)
        self.shutdown = self._wrap_skip(self.shutdown, 'skip_shutdown')

    def override_parameters(self, parameters: Mapping[str, Any]):
        """Override the procedure parameters with a dictionary. It will update
        the instance attributes with the new values.

        :param parameters: Dictionary with the parameters to override
        """
        self._apply_parameter_config(self, parameters)

    @staticmethod
    def _apply_parameter_config(target, parameters: Mapping[str, Any]):
        """Apply a dictionary of parameters to the target's attributes.

        :param parameters: Dictionary with the parameters to override
        """
        for key, value in parameters.items():
            if not hasattr(target, key):
                continue

            param = getattr(target, key, None)
            if not isinstance(param, (Parameter, Metadata)):
                continue

            if not isinstance(value, Mapping):
                value = {'value': value}

            for k, v in value.items():
                try:
                    setattr(param, k, v)
                except AttributeError:
                    target_class = getattr(target, '__class__', target)
                    log.error(f"Error updating parameter {key} in {target_class.__name__}")

    def _wrap_skip(self, method, flag_name: str, fallback=None):
        """Wraps a method to skip execution if a flag is set to True.
        If the flag is set to True, it will execute the fallback function
        if it is callable, or return the fallback value. Otherwise, it will run
        the method as usual.

        :param method: Method to wrap
        :param flag_name: Name of the flag to check as an attribute
        :param fallback: Function to execute or value to return if the flag is True
        """
        @wraps(method)
        def wrapper(*args, **kwargs):
            if getattr(self, flag_name, False):
                log.info(f"Skipping {method.__name__} for {type(self).__name__}")
                return fallback(*args, **kwargs) if callable(fallback) else fallback

            return method(*args, **kwargs)
        return wrapper

    @classmethod
    def configure_class(cls, config_dict: MutableMapping[str, Any]):
        """Load configuration from a dictionary and update the class attributes.

        :param config_dict: Dictionary with the configuration
        """
        # Copy parameters from parent classes to avoid sharing the same instance
        for name, value in inspect.getmembers(cls, lambda x: isinstance(x, Parameter)):
            setattr(cls, name, deepcopy(value))

        parameters: dict = config_dict.pop('parameters', {})
        cls._apply_parameter_config(cls, parameters)

        for key, value in config_dict.items():
            setattr(cls, key, value)
