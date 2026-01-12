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
        from hydra.utils import instantiate as hydra_instantiate
        from omegaconf import OmegaConf

        # Convert to regular dict and instantiate the 'target' field for each instrument
        instruments_dict = {}
        for key in CONFIG.instruments:
            # Convert each instrument config to a regular dict
            inst_config = OmegaConf.to_container(CONFIG.instruments[key], resolve=True)

            # Instantiate the 'target' field to get the actual class
            if 'target' in inst_config and inst_config['target'] is not None:
                inst_config['target'] = hydra_instantiate(inst_config['target'])

            # Add debug flag if in debug mode
            if CONFIG._session.args.debug:
                if 'kwargs' not in inst_config or inst_config['kwargs'] is None:
                    inst_config['kwargs'] = {}
                inst_config['kwargs']['debug'] = True

            instruments_dict[key] = inst_config

        # Use a simple dict wrapper that provides attribute access and deepcopy
        class InstrumentDict(dict):
            def __getattr__(self, key):
                return deepcopy(self[key])

        _instruments = InstrumentDict(instruments_dict)
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
