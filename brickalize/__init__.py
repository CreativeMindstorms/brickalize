# brickalize/__init__.py
"""
Brickalize: Convert 3D models into LEGO-like brick structures.
"""

__version__ = "1.0"  # Should match version in pyproject.toml

# Import the main classes to make them available at the package level
from .bricks import Brick, BrickSet
from .model import BrickModel
from .visualizer import BrickModelVisualizer
from .converter import Brickalizer

# Define __all__ for explicit export control
__all__ = [
    "Brick",
    "BrickSet",
    "BrickModel",
    "BrickModelVisualizer",
    "Brickalizer",
    "__version__",
]