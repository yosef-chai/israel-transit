"""Load the integration's pure-Python modules without pulling in Home Assistant.

``api`` and ``rail_stations`` use relative imports, so they need to live in a
package -- but importing the real package would execute ``__init__.py`` and
require a Home Assistant install. A synthetic namespace package pointed at the
component directory gives us the imports without the dependency.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

PACKAGE = "israel_transit_under_test"
COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "israel_transit"

if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(COMPONENT)]
    sys.modules[PACKAGE] = package
