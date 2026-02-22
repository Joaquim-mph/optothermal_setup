"""Data model for procedure items in sequence builder."""

from dataclasses import dataclass, field
from typing import Any

from pymeasure.experiment import Procedure


@dataclass
class ProcedureItemModel:
    """Data model for a procedure in the sequence builder.

    Attributes:
        procedure_class: The procedure class type
        parameters: Dictionary mapping parameter names to their configuration
                   (value, group_by, etc.)
        sequencer_config: Optional sequencer string for parameter sweeps
        is_expanded: Whether the item is expanded in the UI
    """

    procedure_class: type[Procedure]
    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)
    sequencer_config: str | None = None
    is_expanded: bool = False
