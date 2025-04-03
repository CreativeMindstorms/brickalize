# examples/basic_usage.py
from brickalize import (
    Brick,
    BrickSet,
    BrickModel, # Import BrickModel if needed directly in example
    BrickModelVisualizer,
    Brickalizer
)
import numpy as np

# Initialize variables
stl_file = 'model.stl'
grid_voxel_count = 10
grid_direction = "x"
brick_set = BrickSet([Brick(1, 2), Brick(1, 4), Brick(2, 2), Brick(1, 1), Brick(1, 3), Brick(2, 4), Brick(1, 6), Brick(1, 1, True), Brick(1, 2, True)])

# Voxelize the model
brick_array = Brickalizer.voxelize_stl(stl_file, grid_voxel_count, grid_direction, fast_mode=True)

# Only keep the shell of the model, making it hollow
boundary_array = Brickalizer.extract_shell_from_3d_array(brick_array)

# Convert to a brickmodel
brick_model = Brickalizer.array_to_brick_model(boundary_array, brick_set)

# Generate support
support_array = Brickalizer.generate_support(brick_model, boundary_array)

# Add support to the brick model
brick_model = Brickalizer.array_to_brick_model(support_array, brick_set, brick_model, is_support=True)

# Check if all voxels that should be occupied are occupied
test_array = Brickalizer.brick_model_to_array(brick_model)
assert np.array_equal(boundary_array, test_array), "The original and converted arrays are not the same!"

# Normalize the brick model to ensure it starts at (0,0,0)
# Can be helpful in situations where the brick_model is used in a different program
brick_model.normalize()

# Create a 3D mesh
mesh_list = BrickModelVisualizer.draw_model(brick_array, support_array) # Optimized for only visible faces

# Create a 3D mesh for each brick
mesh_brick_list = BrickModelVisualizer.draw_model_individual_bricks(brick_model) # Non-optimized, drawing all faces

# Save the model as mesh or images of each layer
BrickModelVisualizer.save_model(mesh_list, file_path="brick_model.stl")
BrickModelVisualizer.save_as_images(brick_model, dir_path="images")

# Visualize/show the model
BrickModelVisualizer.show_model(mesh_list)