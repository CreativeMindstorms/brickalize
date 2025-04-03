# brickalize/converter.py
"""
Provides the Brickalizer class for converting 3D mesh files (like STL)
into voxel arrays and subsequently into BrickModel objects using a specific
layer-filling algorithm.
"""

import numpy as np # Arrays
import trimesh  # For loading and processing mesh files (STL)
from tqdm import tqdm  # For progress bars during long operations
from scipy.ndimage import binary_erosion  # For shell extraction

# Import necessary classes from other modules within the package
from .bricks import Brick, BrickSet  # For default height, brick info, and sets
from .model import BrickModel        # For creating the final model object


class Brickalizer:
    @classmethod
    def voxelize_stl(cls, stl_file, grid_voxel_count=10, grid_direction="z", fast_mode=False, threshold=0.5, aspect_ratio=Brick.height):
        """
        Voxelizes an STL file into a grid of voxels, using a specified number of voxels in one direction and an aspect ratio for others.

        Args:
            stl_file (str): Path to the STL file.
            grid_voxel_count (int): The number of voxels in the specified direction (X, Y, or Z).
            grid_direction (str): The direction ('x', 'y', or 'z') in which to specify the number of voxels.
            fast_mode (bool): If True, uses only the center point of each voxel for intersection checking instead of 8 points spaced inside the voxel, with the threshold.
            threshold (float): Threshold for mesh intersection, determines the "solid" region inside the mesh. (0 to 1, where 1 means all 8 corners must be inside)
            aspect_ratio (float): Size of the z axis compared to the x and y axis.
        
        Returns:
            np.ndarray: A 3D binary numpy array [z,x,y]
        """
        # Load the STL file using trimesh
        mesh = trimesh.load_mesh(stl_file)
        
        # Calculate the mesh bounding box
        min_bound, max_bound = mesh.bounds
        dimensions = max_bound - min_bound

        # Adjust the grid size according to the given direction and aspect ratio (z=aspect_ratio * x or y)
        if grid_direction == "x":
            grid_size = (grid_voxel_count, int(grid_voxel_count * (dimensions[1] / dimensions[0])), int(grid_voxel_count * (dimensions[2] / dimensions[0]) / aspect_ratio))
        elif grid_direction == "y":
            grid_size = (int(grid_voxel_count * (dimensions[0] / dimensions[1])), grid_voxel_count, int(grid_voxel_count * (dimensions[2] / dimensions[1]) / aspect_ratio))
        elif grid_direction == "z":
            # Apply the aspect ratio inversely: z is stretched, x and y are scaled down by aspect_ratio
            grid_size = (
                grid_voxel_count * (aspect_ratio * dimensions[0] / dimensions[2]),  # x
                grid_voxel_count * (aspect_ratio * dimensions[1] / dimensions[2]),  # y
                grid_voxel_count  # z
            )
        else:
            raise ValueError("grid_direction must be one of 'x', 'y', or 'z'.")

        # Calculate the voxel size for each direction based on the new grid size
        voxel_size = [(max_bound[i] - min_bound[i]) / grid_size[i] for i in range(3)]

        # Create a grid of coordinates (x, y, z)
        grid_x, grid_y, grid_z = np.meshgrid(
            np.arange(grid_size[0]),
            np.arange(grid_size[1]),
            np.arange(grid_size[2]),
            indexing="ij"
        )
        
        # Convert grid indices to world coordinates
        grid_coords = np.vstack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel()]).T

        # Create a list to store the coordinates of voxels that intersect sufficiently
        intersecting_voxels = set()
        
        if fast_mode:
            # Check each voxel
            for voxel_coords in tqdm(grid_coords, desc="Creating model...."):
                # Get the world coordinates of the center of the voxel
                voxel_center = (voxel_coords + 0.5) * voxel_size + min_bound

                # If it is inside the mesh, save it
                if mesh.contains([voxel_center]):
                    intersecting_voxels.add((int(voxel_coords[0]), int(voxel_coords[1]), int(voxel_coords[2])))

        else:
            # Check each voxel
            for voxel_coords in tqdm(grid_coords, desc="Creating model...."):
                # Get the world coordinates of the center of the voxel
                voxel_center = (voxel_coords + 0.5) * voxel_size + min_bound

                # Calculate the 8 corner points of the voxel, offset by -0.33 and 0.33 along each axis
                corners = []
                for dx in [-0.33, 0.33]:
                    for dy in [-0.33, 0.33]:
                        for dz in [-0.33, 0.33]:
                            corner = voxel_center + np.array([dx, dy, dz]) * voxel_size
                            corners.append(corner)

                # Count how many of the 8 corner points are inside the mesh
                inside_count = sum(mesh.contains(np.array([corner])) for corner in corners)

                # If the number of corners inside the mesh is greater than or equal to the threshold, it's considered an intersecting voxel
                if inside_count >= threshold * len(corners):
                    intersecting_voxels.add((int(voxel_coords[0]), int(voxel_coords[1]), int(voxel_coords[2])))
        
        array_3d = cls.__convert_coords_to_3d_array(intersecting_voxels)
        return array_3d

    @staticmethod
    def __convert_coords_to_3d_array(coords: set[tuple]):
        """
        Converts a set of coordinates to a 3D numpy array.

        Args:
            coords (set[tuple]): A set containing tuples of integers (x, y, z)
        
            Returns:
            np.ndarray: A 3D numpy array [z,x,y]
        """
        # Determine the maximum bounds for the array
        max_x = max(coord[0] for coord in coords) + 1
        max_y = max(coord[1] for coord in coords) + 1
        max_z = max(coord[2] for coord in coords) + 1
        
        # Create a 3D array filled with False
        array = np.zeros((max_z, max_x, max_y), dtype=bool)
        
        # Set True for the given coordinates
        for x, y, z in coords:
            array[z, x, y] = True
        
        return array

    @staticmethod
    def extract_shell_from_3d_array(array: np.ndarray):
        """
        Extract the outermost shell from a 3D binary array and makes everything inside False.

        Args:
            array (np.ndarray): A 3D binary array [z,x,y]
        
        Returns:
            np.ndarray: A 3D binary array [z,x,y]
        """
        
        # Perform binary erosion with a 3x3x3 structuring element
        eroded = binary_erosion(array, structure=np.ones((3, 3, 3)))
        
        # Subtract the eroded version from the original to get only the boundary
        boundaries = array & ~eroded
        
        return boundaries

    @classmethod
    def array_to_brick_model(cls, voxel_array: np.ndarray, brick_set: BrickSet, brick_model: BrickModel = None, is_support = False) -> BrickModel:
        """
        Algorithm to place bricks in a brick model from a brick set, according to a 3D binary array specifying which voxels are occupied.

        Args:
            voxel_array (np.ndarray): A 3D binary numpy array
            brick_set (BrickSet): A set of Bricks
            brick_model (BrickModel, optional): A BrickModel to place the bricks in. Creates a new one if not provided (None).
            is_support (bool): Whether the bricks in the array are support bricks or not
        
        Returns:
            BrickModel: A model containing bricks from brick_set in the shape of the voxel_array
        """

        if brick_model is None:
            brick_model = BrickModel(Brick.height)

        z_size, x_size, y_size = voxel_array.shape

        directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]  # Right, Up, Left, Down

        # Go over every layer
        for z in tqdm(range(z_size), desc="Choosing bricks..."):

            # Start at the origin (front left bottom) and move right
            x, y, d, next_d = 0, 0, 0, 1
            
            # Keep track of visited voxels
            visited = np.zeros_like(voxel_array[z], dtype=bool)

            # Keep track of the occupied voxels, where True is still to be occupied
            occupied = np.copy(voxel_array[z])

            brick_w = []
            previous_x, previous_y = 0, 0

            # Loop for every voxel in the layer
            for _ in range(x_size * y_size):

                # If the current voxel isn't occupied while it should be
                if occupied[x,y]:
                    # Determine the length
                    brick_l = cls.__get_available_length(occupied, x, y, directions[next_d])

                    # If the previous length was the same
                    if brick_l in brick_w or len(brick_w) == 0:
                        # Increase the brick width
                        brick_w.append(brick_l)

                    # If the previous length wasn't the same
                    else:
                        # Place the previous brick
                        occupied = cls.__place_bricks(brick_model, brick_set, occupied, brick_w[0], len(brick_w), previous_x, previous_y, z, directions[next_d], is_support=is_support)

                        # Start a new brick
                        brick_w = [brick_l]

                # If the current voxel is already occupied or shouldn't be occupied
                else:
                    if len(brick_w) != 0:
                        # Place the previous brick if there is still one
                        occupied = cls.__place_bricks(brick_model, brick_set, occupied, brick_w[0], len(brick_w), previous_x, previous_y, z, directions[next_d], is_support=is_support)
                        # Start new brick
                        brick_w = []

                # Mark as visited and get potential next voxel coords
                visited[x, y] = True
                nx, ny = x + directions[d][0], y + directions[d][1]

                previous_x, previous_y = x, y

                # If next voxel not visited, update
                if 0 <= nx < x_size and 0 <= ny < y_size and not visited[nx, ny]:
                    x, y = nx, ny
                    
                # Else change direction and update voxel coords
                else:
                    # Place the brick in progress if there is one
                    if len(brick_w) != 0:
                        occupied = cls.__place_bricks(brick_model, brick_set, occupied, brick_w[0], len(brick_w), x, y, z, directions[next_d], is_support=is_support)
                    
                        # Start new brick
                        brick_w = []

                    d = next_d  # Change direction
                    next_d = (d + 1) % 4
                    x, y = x + directions[d][0], y + directions[d][1]


        return brick_model

    @classmethod
    def generate_support(cls,
                         brick_model: BrickModel,
                         model_array: np.ndarray
                         ) -> np.ndarray:
        """
        Generates sparse pillar support based on a new ground definition.
        Checks if a building brick has at least one stud with a solid connection
        (all True in model_array) down to the lowest occupied layer in brick_model.
        If not, evaluates pillars from all studs of the floating brick, chooses
        the one requiring the fewest new support voxels, and generates that pillar
        downwards, skipping existing model parts and stopping at the lowest layer
        or other support.

        The conceptual "ground" is considered to be just below the minimum
        Z index present in the brick_model.

        Args:
            brick_model (BrickModel): Used to identify building bricks, dimensions,
                                      and the lowest occupied layer.
            model_array (np.ndarray): 3D boolean array [z, x, y] representing initial bricks.

        Returns:
            np.ndarray: 3D boolean array [z, x, y] where True indicates needed support.
        Raises:
            TypeError, ValueError: For invalid inputs or mismatched dimensions.
        """
        # --- Input Validation ---
        if not isinstance(brick_model, BrickModel):
            raise TypeError("Input 'brick_model' must be a BrickModel instance.")
        if not isinstance(model_array, np.ndarray) or model_array.ndim != 3:
             raise TypeError("Input 'model_array' must be a 3D numpy array.")

        if brick_model.is_empty:
            print("Skipping support generation for empty model.")
            return np.zeros_like(model_array, dtype=bool)

        # --- Dimension Setup & Ground Definition ---
        layer_indices = sorted([k for k in brick_model.layers if brick_model.layers[k]]) # Filter empty layers
        if not layer_indices:
            print("Skipping support generation for model with no bricks.")
            return np.zeros_like(model_array, dtype=bool)

        # Define the effective ground level: the lowest Z index with bricks
        min_z_occupied = layer_indices[0]
        max_z_index = layer_indices[-1]

        # Use model_array's actual shape for operations
        size_z, size_x, size_y = model_array.shape

        # Adjust max_z_index if model_array's Z is shorter than brick_model expects
        if max_z_index >= size_z:
             print(f"Warning: brick_model max_z ({max_z_index}) exceeds "
                   f"model_array z-dimension ({size_z}). Clamping max_z.")
             max_z_index = size_z - 1

        # If the lowest occupied layer is outside array bounds, something is wrong
        if min_z_occupied >= size_z or min_z_occupied < 0:
             raise ValueError(f"Lowest occupied layer ({min_z_occupied}) is outside "
                              f"model_array z-bounds [0, {size_z-1}).")
        if max_z_index < min_z_occupied: # No layers to check above ground
             return np.zeros_like(model_array, dtype=bool)

        # --- Coordinate System Adjustment ---
        min_coords_model = brick_model.min # Get min coords (x,y,z) from model
        min_x_int = int(min_coords_model[0])
        min_y_int = int(min_coords_model[1])

        # --- Initialize Output Array ---
        support_array = np.zeros((size_z, size_x, size_y), dtype=bool)

        # --- Iterate top-down ---
        # Check layers z from max_z down to the layer *above* the lowest occupied one.
        # Bricks at min_z_occupied are considered grounded.
        # The range stops *before* min_z_occupied.
        for z in tqdm(range(max_z_index, min_z_occupied, -1), desc="Generating support"):

            layer_bricks_at_z = brick_model.layers.get(z, [])
            if not layer_bricks_at_z: continue

            # Check only BUILDING bricks at layer z to initiate support
            for brick in layer_bricks_at_z:
                 # Skip bricks marked explicitly as support originators if applicable
                 if brick.get("support", False): # Skip if this brick IS support
                     continue

                 bx, by = brick["position"]; bw, bd = brick["size"]
                 # Convert brick's base position to array indices
                 bx_idx_base = bx - min_x_int
                 by_idx_base = by - min_y_int

                 # --- Check if this building brick is floating ---
                 is_floating = True # Assume floating until proven otherwise
                 # Iterate through each stud (ax, ay) in the brick's footprint
                 for ix in range(bw):
                     for iy in range(bd):
                         # Stud's index coordinates
                         ax = bx_idx_base + ix
                         ay = by_idx_base + iy

                         # Clamp coordinates to be valid array indices before checking column
                         ax_clamped = max(0, min(size_x - 1, ax))
                         ay_clamped = max(0, min(size_y - 1, ay))

                         # Skip studs outside array bounds (shouldn't happen with proper array generation)
                         if ax != ax_clamped or ay != ay_clamped:
                             continue

                         # Check if the column below this stud is solid in the model
                         # down to the lowest occupied layer (min_z_occupied)
                         column_below_is_solid = True
                         # Check layers from z-1 down to min_z_occupied (inclusive)
                         for k in range(z - 1, min_z_occupied - 1, -1):
                             if not model_array[k, ax_clamped, ay_clamped]:
                                 column_below_is_solid = False
                                 break # Found a gap, this stud is not supported by model

                         if column_below_is_solid:
                             is_floating = False # Found a supported stud, brick is not floating
                             break # Stop checking studs for this brick

                 # --- End of floating check ---


                 # --- If floating, find the best stud for ONE pillar ---
                 if is_floating:
                     min_pillar_voxels = float('inf')
                     best_stud_coords = None # Store (ax, ay) of best stud

                     # --- Evaluate pillar cost for each stud ---
                     for ix in range(bw):
                         for iy in range(bd):
                             # Pillar's potential start coordinates (under the stud)
                             pillar_x = bx_idx_base + ix
                             pillar_y = by_idx_base + iy

                             # Clamp coordinates
                             pillar_x_clamped = max(0, min(size_x - 1, pillar_x))
                             pillar_y_clamped = max(0, min(size_y - 1, pillar_y))

                             # Skip if clamped coords are not the original (out of bounds)
                             if pillar_x != pillar_x_clamped or pillar_y != pillar_y_clamped:
                                 continue

                             # --- Simulate pillar generation for THIS stud to count voxels ---
                             current_pillar_voxels = 0
                             requires_support_voxels = False

                             # Pillar goes from z-1 down to min_z_occupied (inclusive)
                             for pillar_z in range(z - 1, min_z_occupied - 1, -1):
                                 # 1. Occupied by model part? Pillar continues below, costs 0 here.
                                 if model_array[pillar_z, pillar_x_clamped, pillar_y_clamped]:
                                     continue

                                 # 2. Already supported by another pillar? Stop path, costs 0 here.
                                 if support_array[pillar_z, pillar_x_clamped, pillar_y_clamped]:
                                     requires_support_voxels = True # Needed support up to here
                                     break # Stop simulating down this path

                                 # --- If we reach here, the spot needs a *new* support voxel ---
                                 requires_support_voxels = True
                                 current_pillar_voxels += 1 # Count this needed voxel

                             # --- Compare cost for this stud ---
                             # Only consider paths that actually needed new voxels
                             if requires_support_voxels and current_pillar_voxels < min_pillar_voxels:
                                 min_pillar_voxels = current_pillar_voxels
                                 best_stud_coords = (pillar_x_clamped, pillar_y_clamped)

                     # --- Generate the chosen pillar ---
                     if best_stud_coords is not None:
                         pillar_place_x, pillar_place_y = best_stud_coords

                         # Generate pillar downwards from z-1 down to min_z_occupied
                         for pillar_z in range(z - 1, min_z_occupied - 1, -1):
                             # Check Pillar Stopping/Skipping Conditions
                             # 1. Occupied by model part? Skip placing support here.
                             if model_array[pillar_z, pillar_place_x, pillar_place_y]:
                                 continue

                             # 2. Already supported by another pillar? Stop placing down this path.
                             if support_array[pillar_z, pillar_place_x, pillar_place_y]:
                                 break

                             # --- Place Support ---
                             support_array[pillar_z, pillar_place_x, pillar_place_y] = True
                     # else: No valid pillar placement requiring new voxels was found.

        return support_array

    @staticmethod
    def brick_model_to_array(brick_model: BrickModel, include_support: bool = False) -> np.ndarray:
        """
        Converts a BrickModel to a 3D binary numpy array.

        Args:
            brick_model (BrickModel): A BrickModel instance.
            include_support (bool): Whether to include support bricks in the output array.

        Returns:
            np.ndarray: A 3D binary numpy array [z,x,y] where True indicates occupied space.
        """
        if not isinstance(brick_model, BrickModel):
            raise TypeError("Input 'brick_model' must be a BrickModel instance.")

        # Use the provided size or the size of the brick model
        array = np.zeros((brick_model.size[2], brick_model.size[0], brick_model.size[1]), dtype=bool)
        min = brick_model.min
        for z, layer in brick_model.layers.items():
            for brick in layer:
                # Skip support bricks if not requested
                if not include_support and brick["support"]:
                    continue
                # Get the brick's position and size
                x, y = brick["position"]
                w, l = brick["size"]
                # Convert to array indices
                x_adj = x - brick_model.min[0]
                y_adj = y - brick_model.min[1]
                # Mark the corresponding area in the array as occupied
                array[z - min[2], x_adj - min[0]:x_adj + w - min[0], y_adj - min[1]:y_adj + l - min[1]] = True
        return array

    @staticmethod
    def __get_available_length(array: np.ndarray, x: int, y: int, direction: tuple):
        """
        Check how many True values there are in array starting at x and moving in direction
        
        Args:
            array (np.ndarray): The 2d binary array
            x (int): origin
            y (int): origin
            direction (tuple[int]): The dirction in which to check (e.g. (-1,0))
        
        Returns:
            int: The amount of True values in the direction including the origin
        """
        # Initialize variables
        count = 0
        current_x, current_y = x, y
        
        # Traverse in the given direction until the bounds of the array are exceeded or we encounter a False value
        while 0 <= current_x < array.shape[0] and 0 <= current_y < array.shape[1] and array[current_x, current_y]:
            count += 1
            current_x += direction[0]
            current_y += direction[1]
        
        return count

    @staticmethod
    def __place_bricks(brick_model: BrickModel, brick_set: BrickSet, array: np.ndarray, brick_l: int, brick_w:int, brick_x: int, brick_y: int, z: int, l_direction: tuple, is_support: bool = False) -> np.ndarray:
        """
        Attempt to place a brick in the brick model and mark it as occupied in the array.
        If there is no brick with the specified brick_size, fill it in with available bricks, prioritizing the length of the target brick.
        Only assures the row from x in -w_direction is filled in.
        
        Args:
            brick_model (BrickModel): A brickmodel to place the brick in
            brick_set (BrickSet): A BrickSet containing various sizes of Bricks to fill in the space
            array (np.ndarray): A binary 2d array to keep track of occupied spaces
            brick_l (int): The length of the brick
            brick_w (int): The width of the brick
            brick_x (int): The latest column
            brick_y (int): The latest row
            z (int): The layer
            l_direction (tuple): The direction of brick_l (e.g. (-1,0) for x and y respectively)
            is_support (bool): Whether the bricks are support bricks or not
        
        Returns:
            np.ndarray: Updated binary 2d array
        """

        def place_brick(brick_model: BrickModel, array: np.ndarray, x: int, y: int, z: int, w: int, l: int):
            """
            Places a brick in the brick model and marks the space in array as occupied.

            Args:
                brick_model (BrickModel): A brickmodel to place the brick in
                array (np.ndarray): A binary 2d array to keep track of occupied spaces
                x (int): The x-origin (left)
                y (int): The y-origin (front (top in array))
                z (int): The height
                w (int): The width of the brick in x direction
                l (int): The length of the brick in y direction

            Returns:
                np.ndarray: Updated binary 2d array
            """
            brick_model.place_brick(((w,l), is_support), (x,y,z))

            # Iterate over the rectangular area defined by (x, y) and (w, h)
            for i in range(y, y + l):
                for j in range(x, x + w):
                    # Ensure the indices are within bounds
                    if 0 <= i < array.shape[1] and 0 <= j < array.shape[0]:
                        # Mark them
                        array[j, i] = ~array[j, i]

            return array

        def get_origin(brick_x, brick_y, brick_w, brick_l, l_direction):

            # Normalize the x, y w and l values using l_direction
            if l_direction == (1, 0):
                x = brick_x
                y = brick_y
                w = brick_l
                l = brick_w
            elif l_direction == (0, 1):
                x = brick_x - brick_w + 1
                y = brick_y
                w = brick_w
                l = brick_l
            elif l_direction == (-1, 0):
                x = brick_x - brick_l + 1
                y = brick_y - brick_w + 1
                w = brick_l
                l = brick_w
            else:
                x = brick_x
                y = brick_y - brick_l + 1
                w = brick_w
                l = brick_l
            return x,y,w,l

        def max_under_limit(viable_integers, max_integer):
            filtered = [x for x in viable_integers if x <= max_integer]
            return max(filtered, default=None)  # Returns None if no valid numbers are found

        # If there exists a brick that fits the targeted space perfectly, place it immediately
        dimensions = brick_set.get_building_bricks_by_dimension(brick_l) if not is_support else brick_set.get_support_bricks_by_dimension(brick_l)
        if brick_w in dimensions:
            x,y,w,l = get_origin(brick_x, brick_y, brick_w, brick_l, l_direction)
            array = place_brick(brick_model, array, x, y, z, w, l)
            return array
        
        possible_lengths = brick_set.get_building_brick_dimensions() if not is_support else brick_set.get_support_brick_dimensions()
        w_counter = 0
        while w_counter < brick_w:
            fits = False
            max_l = brick_l
            max_w = brick_w
            while not fits:
                # Get largest fitting length
                actual_l = max_under_limit(possible_lengths, max_l)
                if actual_l != None:

                    # Get largest fitting width for that length
                    actual_w = brick_set.get_building_bricks_by_dimension(actual_l) if not is_support else brick_set.get_support_bricks_by_dimension(actual_l)
                    actual_w = max_under_limit(actual_w, max_w)
                    if actual_w != None:
                        
                        # If it fits, continue
                        if actual_w <= brick_w-w_counter:
                            fits = True
                        
                        # If it doesn't fit, try a smaller width
                        else:
                            max_w = max_w-1
                    
                    # If it doesn't have any width left, try a smaller length
                    else:
                        max_l = max_l-1
                        max_w = brick_w
                
                # If there is no fitting length, raise an exception
                else:
                    raise Exception("The brick_set does not contain sufficient bricks")

            # Use the new width and length to subtract from the to-be-filled space
            if l_direction[0] == 0:
                x,y,w,l = get_origin(brick_x+l_direction[1]*(-brick_w+actual_w+w_counter), brick_y, actual_w, actual_l, l_direction)
            else:
                x,y,w,l = get_origin(brick_x, brick_y+l_direction[0]*(brick_w-actual_w-w_counter), actual_w, actual_l, l_direction)

            # Place this brick
            array = place_brick(brick_model, array, x, y, z, w, l)

            # Continue until entire width is filled
            w_counter += actual_w

                
        return array
