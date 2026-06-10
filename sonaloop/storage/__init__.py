from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..config import DATA_DIR, database_path, utc_now_iso
from ._base import StoreBase
from ._councils import CouncilsMixin
from ._memory import MemoryMixin
from ._personas import PersonasMixin
from ._prototypes import PrototypesMixin
from ._research import ResearchMixin
from ._schema import SCHEMA
from ._simulation import SimulationMixin
from ._usability_sessions import UsabilitySessionsMixin


class Store(
    PersonasMixin,
    SimulationMixin,
    CouncilsMixin,
    ResearchMixin,
    PrototypesMixin,
    UsabilitySessionsMixin,
    MemoryMixin,
    StoreBase,
):
    pass


__all__ = ["Store", "SCHEMA"]
