# brickalize

[![PyPI version](https://badge.fury.io/py/brickalize.svg)](https://badge.fury.io/py/brickalize)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/pypi/pyversions/brickalize.svg)](https://pypi.org/project/brickalize/)

A Python package for converting 3D models (STL) into LEGO-like brick structures, generating necessary support structures, and visualizing the result in 3D or as layer-by-layer 2D images.

---

## Table of Contents

-   [Introduction](#introduction)
-   [Features](#features)
-   [Installation](#installation)
-   [Usage](#usage)
    -   [Core Workflow Example](#core-workflow-example)
    -   [Key Components](#key-components)
-   [API Overview](#api-overview)
-   [Dependencies](#dependencies)
-   [Contributing](#contributing)
-   [License](#license)
-   [Contact](#contact)

## Introduction

`brickalize` provides tools to take a standard 3D model file (STL) and transform it into a representation made of LEGO-like bricks. It voxelizes the input model, optionally extracts its shell to make it hollow, intelligently places bricks from a user-defined set to build the structure, generates sparse support pillars for overhangs, and offers visualization options including interactive 3D rendering and 2D build instruction images.

This package is useful for hobbyists, LEGO® engineers, or anyone interested in translating digital 3D designs into physically buildable brick models.

## Features

*   **STL Loading:** Loads 3D models from STL files using `trimesh`.
*   **Voxelization:** Converts continuous 3D models into a grid of voxels with configurable resolution, direction, and aspect ratio. Supports fast (center-point) and more accurate (multi-point threshold) voxel occupancy checks.
*   **Shell Extraction:** Option to keep only the outer shell of the voxelized model, creating hollow structures.
*   **Brick Definition:** Define available brick types (dimensions, support status) using the `Brick` class and manage them with `BrickSet`.
*   **Intelligent Brick Placement:** An algorithm (`Brickalizer.array_to_brick_model`) converts the voxel grid into a `BrickModel` by placing bricks from the provided `BrickSet`, optimizing for larger bricks where possible.
*   **Automatic Support Generation:** Generates sparse, pillar-like support structures (`Brickalizer.generate_support`) necessary for overhangs, minimizing material usage compared to dense supports.
*   **Model Representation:** Stores the final structure layer by layer in a `BrickModel` object.
*   **3D Visualization:** Renders the `BrickModel` (including separate colors/transparency for support) in an interactive 3D view using `open3d`.
*   **Mesh Saving:** Saves the generated brick model (including supports) as a single STL file.
*   **2D Layer Images:** Generates detailed 2D images for each layer, suitable for building instructions, with customizable colors, stud overlays, and ghost layer previews.

## Installation

**1. Using pip (Recommended):**

```bash
pip install brickalize
```

**2. Installing from Source (GitHub):**

```bash
pip install git+https://github.com/CreativeMindstorms/brickalize.git
```

This will also install the required dependencies.

## Usage

### Core Workflow Example

Here's a typical workflow using `brickalize`:

```python
import numpy as np
from brickalize import Brick, BrickSet, Brickalizer, BrickModelVisualizer

# --- 1. Configuration ---
stl_file = 'path/to/your/model.stl'  # Replace with your STL file path
output_dir = 'brickalize_output'      # Directory for output images/STL
output_stl_path = f"{output_dir}/brick_model.stl"

# Define the set of bricks available for building
# Format: Brick(width, length, is_support=False)
# Supports are optional, used only if generate_support is called.
brick_set = BrickSet([
    Brick(1, 1), Brick(1, 2), Brick(1, 3), Brick(1, 4), Brick(1, 6),
    Brick(2, 2), Brick(2, 3), Brick(2, 4),
    # Add support bricks if you plan to generate support
    Brick(1, 1, is_support=True), Brick(1, 2, is_support=True), Brick(2, 2, is_support=True)
])

# Voxelization parameters
grid_voxel_count = 50  # Number of voxels along the specified dimension
grid_direction = "z"   # Voxel count constraint ('x', 'y', or 'z')
use_fast_voxelization = False # True for faster, less accurate voxelization
voxel_threshold = 0.5  # For non-fast mode (0 to 1)

# Output image parameters
import os
os.makedirs(output_dir, exist_ok=True)

# --- 2. Voxelization ---
print("Voxelizing STL model...")
# aspect_ratio defaults to Brick.height (1.2)
voxel_array = Brickalizer.voxelize_stl(
    stl_file,
    grid_voxel_count=grid_voxel_count,
    grid_direction=grid_direction,
    fast_mode=use_fast_voxelization,
    threshold=voxel_threshold
)
print(f"Voxel array shape: {voxel_array.shape}")

# --- 3. (Optional) Shell Extraction ---
# Uncomment the next line to make the model hollow
# print("Extracting shell...")
# voxel_array = Brickalizer.extract_shell_from_3d_array(voxel_array)

# --- 4. Convert Voxel Array to Brick Model ---
print("Converting voxels to building bricks...")
brick_model = Brickalizer.array_to_brick_model(voxel_array, brick_set, is_support=False)
print(f"Initial brick model created with {len(brick_model.layers)} layers.")

# --- 5. Generate Support Structures ---
print("Generating support structures...")
# Needs the original voxel array to know where the model is solid
support_array = Brickalizer.generate_support(brick_model, voxel_array)
print(f"Support array generated. Needs support: {np.any(support_array)}")

# --- 6. Add Support Bricks to the Model ---
if np.any(support_array):
    if not brick_set.has_support:
        print("Warning: Support structures needed, but no support bricks defined in BrickSet.")
    else:
        print("Adding support bricks to the model...")
        # Pass the existing brick_model to add supports to it
        brick_model = Brickalizer.array_to_brick_model(
            support_array,
            brick_set,
            brick_model=brick_model, # Add to existing model
            is_support=True
        )
        print("Support bricks added.")

# --- 7. (Optional) Normalize Model Coordinates ---
# Ensures the model's bottom-left-front corner starts at (0,0,0)
brick_model.normalize()
print("Brick model normalized.")

# --- 8. Visualization and Saving ---

# Generate combined array for visualization (optional, but useful)
model_array_for_vis = Brickalizer.brick_model_to_array(brick_model, include_support=False)
support_array_for_vis = Brickalizer.brick_model_to_array(brick_model, include_support=True) & ~model_array_for_vis

# Option A: Visualize as a combined mesh (faster rendering)
print("Generating combined 3D mesh...")
mesh_list_combined = BrickModelVisualizer.draw_model(
    model_array_for_vis,
    support_array=support_array_for_vis if np.any(support_array_for_vis) else None,
    voxel_height=brick_model.layer_height
)

# Option B: Visualize individual bricks (slower rendering, more detail)
# print("Generating individual brick meshes...")
# mesh_list_individual = BrickModelVisualizer.draw_model_individual_bricks(brick_model)

# Save the combined mesh as STL
print(f"Saving combined mesh to {output_stl_path}...")
saved = BrickModelVisualizer.save_model(mesh_list_combined, file_path=output_stl_path)
if saved: print("STL model saved successfully.")
else: print("Error saving STL model.")

# Save layer-by-layer images
print(f"Saving layer images to '{output_dir}'...")
BrickModelVisualizer.save_as_images(
    brick_model,
    dir_path=output_dir,
    brick_color=(0, 255, 255),    # BGR color for building bricks (Yellow)
    support_color=(200, 200, 255), # BGR color for support bricks (Light Pinkish)
    add_lego_overlay=True,       # Add stud shadows
    show_ghost_layer=True,       # Show previous layer semi-transparently
    pixels_per_stud=20,          # Resolution of images
    line_thickness=0.05          # Relative thickness of brick outlines
)
print("Layer images saved.")

# Show the 3D model (using the combined mesh)
print("Displaying 3D model (Close window to exit)...")
BrickModelVisualizer.show_model(mesh_list_combined)
# Or show individual bricks: BrickModelVisualizer.show_model(mesh_list_individual)

print("Brickalize process complete.")

```

### Key Components

*   **`Brick(d1, d2, is_support=False)`:** Defines a single type of brick. `d1` and `d2` are stud dimensions (e.g., 2x4), `is_support` flags it as a support-only brick.
*   **`BrickSet([Brick(...), ...])`:** Holds a collection of unique `Brick` objects available for the conversion process.
*   **`Brickalizer`:** Contains the static methods for the main conversion steps:
    *   `voxelize_stl()`: STL to 3D numpy array.
    *   `extract_shell_from_3d_array()`: Make the voxel array hollow.
    *   `array_to_brick_model()`: Voxel array to `BrickModel` using a `BrickSet`.
    *   `generate_support()`: Creates a 3D numpy array indicating needed support voxels.
    *   `brick_model_to_array()`: Converts a `BrickModel` back to a 3D numpy array.
*   **`BrickModel`:** Represents the final structure as a dictionary of layers, where each layer contains a list of placed bricks (position, size, support status).
*   **`BrickModelVisualizer`:** Static methods for visualization and saving:
    *   `draw_model()`: Creates `open3d` mesh geometry from voxel/support arrays (efficient).
    *   `draw_model_individual_bricks()`: Creates `open3d` mesh geometry with one mesh per brick (detailed but slower).
    *   `show_model()`: Displays the generated meshes in an interactive window.
    *   `save_model()`: Saves the mesh geometry as an STL file.
    *   `save_as_images()`: Generates 2D PNG images for each layer.

## API Overview

The main components exposed by the package are:

*   **`brickalize.Brick`**: Class representing a single type of LEGO-like brick with dimensions and support status.
*   **`brickalize.BrickSet`**: Class managing a collection of unique `Brick` objects, providing helper methods to query available dimensions.
*   **`brickalize.BrickModel`**: Class representing the layered brick structure, storing placed bricks (size, position, type) per layer.
*   **`brickalize.BrickModelVisualizer`**: Class with static methods for creating 3D visualizations (`open3d`), saving models (STL), and generating 2D layer images (`opencv-python`).
*   **`brickalize.Brickalizer`**: Class with static methods orchestrating the conversion process: loading STL, voxelizing, shell extraction, brick placement, and support generation.
*   **`brickalize.__version__`**: String containing the current package version.

Refer to the docstrings within the code for detailed parameter descriptions.

## Dependencies

The package relies on the following libraries:

*   numpy
*   open3d
*   trimesh
*   tqdm
*   opencv-python
*   scipy

These will be installed automatically when you install `brickalize` using pip.

## Contributing

Contributions are welcome, and I appreciate your interest in improving this project! However, I want to keep this easy to manage, as it is a personal project and a learning experience for me.

1. Open an issue on the [GitHub repository](https://github.com/CreativeMindstorms/brickalize/issues).
2. Fork the Repository: Create a personal copy of the repository by clicking the "Fork" button at the top.
3. Make Changes: Implement your changes in your forked repository. Please keep changes focused and well-documented.
4. Submit a Pull Request (PR): Open a pull request with a clear explanation of your changes. Include why the change is beneficial and how it affects the project.


## License

This project is licensed under the [GPLv3 License](LICENSE). Contributions and modifications are welcome, but they must remain open-source and credit the original author.

## Contact

Sten Nellen (Creative Mindstorms) - creativemindstorms1@gmail.com

Project Link: [https://github.com/CreativeMindstorms/brickalize](https://github.com/CreativeMindstorms/brickalize)

### Disclaimer
This project is a hobby, and while I enjoy working on it, I can’t provide consistent support or assistance. Please feel free to reach out via email for questions or feedback, but responses may be delayed depending on my availability.