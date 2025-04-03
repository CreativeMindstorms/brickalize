=====
Usage
=====

This guide provides instructions and examples on how to use the ``brickalize`` library to convert 3D models into LEGO-like brick structures.

.. seealso::
   For installation instructions, please refer to the :doc:`installation` guide.

Core Workflow Example
---------------------

The most common use case involves loading an STL file, converting it to a voxel representation, building a brick model from those voxels, optionally generating support structures, and finally visualizing or saving the result.

The following script demonstrates this entire process:

.. note::
   You will need an STL file (e.g., named ``model.stl`` in the script's directory) for this example to run. Replace ``'model.stl'`` with the actual path to your file. You might also need to create the output directories (e.g., ``images/``) beforehand, or add ``os.makedirs('images', exist_ok=True)`` to the script.

.. literalinclude:: ../examples/basic_usage.py
   :language: python
   :linenos:

Workflow Explanation
--------------------

Let's break down the steps shown in the example script:

1.  **Import necessary components:**
    Import the required classes from the ``brickalize`` library. The example uses:
    Import classes like ``Brick``, ``BrickSet``, ``Brickalizer``, and ``BrickModelVisualizer``.
2.  **Configuration:**
        *   Define the path to your input ``stl_file``.
        *   Set ``grid_voxel_count`` and ``grid_direction`` to control the resolution and orientation of the voxelization process.
        *   Create a ``BrickSet`` containing all the ``Brick`` sizes (including optional support bricks) available for building the model.
3.  **Voxelization:**
    Use ``Brickalizer.voxelize_stl`` to convert the geometry from the STL file into a 3D NumPy boolean array (``brick_array``), where ``True`` indicates occupied space. Parameters like ``fast_mode`` can be used for quicker, less precise results.
4.  **Shell Extraction (Optional):**
    ``Brickalizer.extract_shell_from_3d_array`` can be used on the ``brick_array`` to make the resulting model hollow, keeping only the outer surfaces. The example uses this ``boundary_array``.
5.  **Convert Voxels to Bricks:**
    ``Brickalizer.array_to_brick_model`` takes the target voxel array (e.g., ``boundary_array``) and the ``BrickSet``, and populates a ``BrickModel`` object by intelligently placing the largest possible bricks from the set to fill the occupied voxels.
6.  **Generate Support:**
    ``Brickalizer.generate_support`` analyzes the placed building bricks in the ``brick_model`` against the original solid shape (``boundary_array`` in this case) to identify overhangs. It returns a new 3D boolean array (``support_array``) indicating where support pillars are required.
7.  **Add Support Bricks:**
    If ``support_array`` contains ``True`` values (meaning support is needed) and the ``BrickSet`` includes support bricks, call ``Brickalizer.array_to_brick_model`` again. This time, pass the ``support_array``, the *existing* ``brick_model`` (to add to it), and set ``is_support=True``.
8.  **Verification (Optional):**
    The example includes an assertion using ``Brickalizer.brick_model_to_array`` to check if the array generated *from* the final ``brick_model`` matches the target array (``boundary_array``). This helps confirm the conversion integrity.
9.  **Normalization (Optional):**
    Calling ``brick_model.normalize()`` modifies the brick positions within the ``BrickModel`` so that the model's minimum corner sits at coordinate (0, 0, 0). This can be useful for consistent positioning or exporting.
10. **Create Visualization Meshes:**
        *   ``BrickModelVisualizer.draw_model`` generates optimized meshes suitable for rendering the overall model shape (using the original ``brick_array`` and ``support_array``).
        *   ``BrickModelVisualizer.draw_model_individual_bricks`` generates a separate mesh for *each individual brick* in the ``brick_model``. This is less performant for viewing but represents the actual brick structure precisely.
11. **Save Output:**
        *   ``BrickModelVisualizer.save_model`` saves one of the generated mesh lists (typically the combined one) to an STL file.
        *   ``BrickModelVisualizer.save_as_images`` renders the ``brick_model`` layer by layer into PNG images, useful for building instructions.
12. **Display Model:**
    ``BrickModelVisualizer.show_model`` opens an interactive 3D window to display one of the generated mesh lists.

Key Components
--------------

Understanding the main classes helps in customizing the process:

**Brick Definition** (``Brick`` and ``BrickSet``)

*   A ``Brick`` object represents a single type of brick, defined by its dimensions (e.g., length, width) and whether it's a support brick. Height is a class property.
*   A ``BrickSet`` holds a collection of unique ``Brick`` objects that the ``Brickalizer`` can use during the conversion process. You must provide at least one non-support brick.

.. code-block:: python
   :caption: Defining a BrickSet

   from brickalize import Brick, BrickSet

   # Define available building bricks
   building_bricks = [
       Brick(1, 1), Brick(1, 2), Brick(1, 4),
       Brick(2, 2), Brick(2, 3), Brick(2, 4)
   ]

   # Define available support bricks (optional)
   support_bricks = [
       Brick(1, 1, is_support=True),
       Brick(2, 2, is_support=True)
   ]

   # Combine them into a set
   my_brick_set = BrickSet(building_bricks + support_bricks)

   print(f"Support available: {my_brick_set.has_support}")

**Conversion Logic** (``Brickalizer``)

*   This class contains static methods that perform the core conversion steps.
*   ``voxelize_stl()``: Converts STL to a 3D boolean NumPy array. Key parameters:
    *   ``grid_voxel_count``, ``grid_direction``: Control resolution.
    *   ``aspect_ratio``: Sets the relative height of voxels (default matches ``Brick.height``).
    *   ``fast_mode``: Uses only voxel centers for occupancy checks (faster, less accurate).
    *   ``threshold``: When ``fast_mode=False``, determines the fraction of voxel corners that must be inside the mesh (0.0 to 1.0).
*   ``extract_shell_from_3d_array()``: Takes a voxel array and returns a new array containing only the outer layer of voxels (hollows the model).
*   ``array_to_brick_model()``: The core algorithm that places bricks from a ``BrickSet`` onto a ``BrickModel`` according to a target voxel array. Can add building or support bricks.
*   ``generate_support()``: Calculates where support structures are needed based on a ``BrickModel`` and a reference voxel array.
*   ``brick_model_to_array()``: Converts a ``BrickModel`` back into a 3D boolean NumPy array.

**Model Representation** (``BrickModel``)

*   Stores the final bricked structure.
*   It's essentially a dictionary where keys are layer indices (Z-height), and values are lists of dictionaries, each representing a placed brick (size, position, support status).
*   Provides properties like ``layers``, ``size``, ``min``, ``max`` and methods like ``normalize()``.

**Output and Visualization** (``BrickModelVisualizer``)

*   This class provides static methods to visualize and save the results.
*   ``draw_model()``: Creates efficient combined meshes from voxel arrays (good for quick visualization).
*   ``draw_model_individual_bricks()``: Creates a mesh list where each element corresponds to a single brick in the ``BrickModel`` (accurate structure, slower rendering).
*   ``save_model()``: Saves a mesh list (from either ``draw_`` method) to an STL file.
*   ``save_as_images()``: Creates layer-by-layer PNG images. Key parameters:
    *   ``brick_color``, ``support_color``: Customize colors (BGR format).
    *   ``add_lego_overlay``: Adds stud shadow effect.
    *   ``show_ghost_layer``: Displays the layer below semi-transparently.
    *   ``pixels_per_stud``: Controls image resolution.
*   ``show_model()``: Opens an interactive ``open3d`` window to view a mesh list.

Customization and Examples
--------------------------

**Voxelization Control**

You can adjust the voxelization result significantly:

.. code-block:: python
   :caption: Adjusting Voxelization

   # Higher resolution along Y axis
   hires_array = Brickalizer.voxelize_stl(stl_file, grid_voxel_count=50, grid_direction="y")

   # More accurate (but slower) voxel check
   accurate_array = Brickalizer.voxelize_stl(stl_file, grid_voxel_count=20, fast_mode=False, threshold=0.6)

   # Different aspect ratio (e.g., for plate-like bricks)
   plate_array = Brickalizer.voxelize_stl(stl_file, grid_voxel_count=10, aspect_ratio=0.4) # Standard height is 1.2

**Using Different Brick Sets**

The choice of bricks dramatically affects the output structure and piece count.

.. code-block:: python
   :caption: Using only 2xN bricks

   from brickalize import Brick, BrickSet, Brickalizer
   # ... (assuming voxel_array exists) ...

   simple_set = BrickSet([Brick(2, 2), Brick(2, 4)]) # Only 2x2 and 2x4 bricks
   simple_model = Brickalizer.array_to_brick_model(voxel_array, simple_set)

   # ... (visualize or process simple_model) ...

**Customizing Image Output**

Tailor the look of the layer images:

.. code-block:: python
   :caption: Customizing Layer Images

   BrickModelVisualizer.save_as_images(
       brick_model,
       dir_path="custom_images",
       brick_color=(255, 0, 0),    # Blue bricks
       support_color=(0, 255, 0),  # Green supports
       add_lego_overlay=False,     # No stud shadows
       show_ghost_layer=False,     # Don't show layer below
       pixels_per_stud=30          # Higher resolution
   )

**Visualizing Individual Bricks**

To see the model composed of its actual constituent bricks (instead of an optimized surface mesh):

.. code-block:: python
   :caption: Showing Individual Bricks

   # Generate list of meshes, one per brick
   mesh_brick_list = BrickModelVisualizer.draw_model_individual_bricks(brick_model)

   # Show these individual meshes
   BrickModelVisualizer.show_model(mesh_brick_list)