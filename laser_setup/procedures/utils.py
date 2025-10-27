from copy import deepcopy

from omegaconf import DictConfig

from ..config import CONFIG, instantiate


class DeepCopyDictConfig(DictConfig):
    """Deepcopy of the DictConfig class. It allows to deepcopy the
    parameters when they are accessed.
    """
    def __getitem__(self, key):
        item = super().__getitem__(key)
        if isinstance(item, DictConfig):
            return type(self)(item)
        return deepcopy(item)

    def __getattr__(self, key):
        item = super().__getattr__(key)
        if isinstance(item, DictConfig):
            return type(self)(item)
        return deepcopy(item)


# Lazy instantiation - don't instantiate adapters until actually used
_instruments = None
_parameters = None

def _get_instruments():
    global _instruments
    if _instruments is None:
        # Instantiate without creating adapter objects (just the config)
        _instruments = DeepCopyDictConfig(CONFIG.instruments)
        if CONFIG._session.args.debug:
            for key in _instruments:
                if hasattr(_instruments[key], 'kwargs') and _instruments[key].kwargs is not None:
                    _instruments[key].kwargs.debug = True
    return _instruments

def _get_parameters():
    global _parameters
    if _parameters is None:
        _parameters = instantiate(CONFIG.parameters)
    return _parameters

# Create properties that lazy-load on first access
class _LazyLoader:
    @property
    def Instruments(self):
        return _get_instruments()

    @property
    def Parameters(self):
        return _get_parameters()

_loader = _LazyLoader()
Instruments = _loader.Instruments
Parameters = _loader.Parameters
