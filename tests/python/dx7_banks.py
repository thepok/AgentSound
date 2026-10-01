"""The Yamaha DX7 ROM banks (assets/dx7/*.syx) are not part of the repository (see assets/dx7/README.md).

Tests that render or validate DX7 voices skip without them: `@needs_dx7` on a test (or class), `missing_dx7(x)`
to leave DX7 patches / instruments out of a library-wide engine check when the banks are absent.
"""

import unittest

from agentsound.catalog import DX7_NO_BANKS, dx7_banks_installed
from agentsound.patches import Instrument, Patch

HAVE_DX7 = dx7_banks_installed()
needs_dx7 = unittest.skipUnless(HAVE_DX7, DX7_NO_BANKS)


def uses_dx7(x) -> bool:
    """True when a Patch / Instrument plays a DX7 voice (itself or one of its stack layers)."""
    ins = x.instrument if isinstance(x, Patch) else x
    if not isinstance(ins, Instrument):
        return False
    if ins.type == 'dx7':
        return True
    return ins.type == 'stack' and any(uses_dx7(layer.instrument) for layer in ins.params.get('layers', ()))


def missing_dx7(x) -> bool:
    """True when x plays a DX7 voice and the ROM banks are not installed (leave it out of an engine check)."""
    return not HAVE_DX7 and uses_dx7(x)
