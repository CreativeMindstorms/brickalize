# brickalize/model.py
"""
Defines the BrickModel class, which represents the assembled structure
of bricks in layers.
"""

# Import necessary classes from other modules within the package
from .bricks import Brick   # To access its default height constant `Brick.height`

# No other external libraries like numpy, open3d, etc., are directly used
# within the BrickModel class logic itself. They are used by classes
# that operate on or visualize the BrickModel.


class BrickModel:

    def __init__(self, layer_height:float = Brick.height):
        """
        Initializes an empty brick model.
        
        Args:
            layer_height (float):

        Raises:
            TypeError: if layer_height is not a float.
            ValueError: if the layer_height is not larger than 0
        """
        self.__verify_inputs(layer_height)
        self.__layers = {}
        self.__layer_height = layer_height

    def __verify_inputs(self, layer_height:float):
        if not isinstance(layer_height, float):
            raise TypeError("Layer height must be a float.")
        if layer_height <= 0:
            raise ValueError("Layer height must be non-zero and positive.")

    @property
    def layer_height(self) -> float:
        """The height of each layer in the model."""
        return self.__layer_height
    
    @property
    def layers(self) -> dict[int, list[dict]]:
        """A dictionary containing all layers and the bricks in each layer."""
        return self.__layers.copy()

    @property
    def is_empty(self) -> bool:
        """bool: True if the model contains no bricks, False otherwise."""
        return not bool(self.__layers) # Check if the layers dictionary is empty

    @property
    def size(self) -> tuple[int, int, int]:
        """The size of the model in bricks (x, y, z)."""
        if len(self.__layers) == 0:
            return (0, 0, 0)
        x_min, y_min, z_min = self.min
        x_max, y_max, z_max = self.max
        return (int(x_max - x_min), int(y_max - y_min), int(z_max - z_min + 1))

    @property
    def min(self) -> tuple[int, int, int]:
        """The minimum x, y, z coordinates of the model in bricks."""
        if len(self.__layers) == 0:
            return (0, 0, 0)
        x_min = min([min([brick["position"][0] for brick in layer]) for layer in self.__layers.values()])
        y_min = min([min([brick["position"][1] for brick in layer]) for layer in self.__layers.values()])
        z_min = min(self.__layers.keys())
        return (x_min, y_min, z_min)
    
    @property
    def max(self) -> tuple[int, int, int]:
        """The maximum x, y, z coordinates of the model in bricks."""
        if len(self.__layers) == 0:
            return (0, 0, 0)
        x_max = max([max([brick["position"][0] + brick["size"][0] for brick in layer]) for layer in self.__layers.values()])
        y_max = max([max([brick["position"][1] + brick["size"][1] for brick in layer]) for layer in self.__layers.values()])
        z_max = max(self.__layers.keys())
        return (x_max, y_max, z_max)

    def place_brick(self, oriented_brick:tuple[tuple[int, int], bool], position:tuple[int, int, int]) -> bool:
        """
        Attempt to place a brick in the model at a specified position.
        
        Args:
            oriented_brick (tuple[tuple[int, int], bool]): tuple containing a tuple with the size in x and y direction and a bool that is True if the brick is support. ((x, y), is_support)
            position (tuple[int, int, int]): The x, y and z coordinates, for the left, front, bottom corner, respectively
        
        Returns:
            bool: Whether the placement was succesful or not

        Raises:
            TypeError: If the inputs are invalid
        """
        # Verify the inputs
        if not isinstance(oriented_brick, tuple) and not isinstance(oriented_brick, list):
            raise TypeError("oriented_brick must be a tuple or list.")
        if (not isinstance(oriented_brick[0], tuple) and not isinstance(oriented_brick[0], list)) or not isinstance(oriented_brick[0][0], int) or not isinstance(oriented_brick[0][1], int):
            raise TypeError("oriented_brick must contain the size in (x,y) format at index 0 (tuple[int]).")
        if (not isinstance(position, tuple) and not isinstance(position, list)) or not isinstance(position[0], int) or not isinstance(position[1], int) or not isinstance(position[2], int):
            raise TypeError("position must contain the coordinates in (x,y,z) format (tuple[int]).")
        if not isinstance(oriented_brick[1], bool):
            raise TypeError("oriented_brick must contain a bool at index 1.")
        

        z = position[2]
        positioned_brick = {"size":(oriented_brick[0][0], oriented_brick[0][1]), "position":(position[0], position[1]), "support":oriented_brick[1]}
        if z in self.__layers:
            for brick in self.__layers[z]:
                if self.__is_overlap(positioned_brick, brick):
                    return False
            self.__layers[z].append(positioned_brick)
            return True
        else:
            self.__layers[z] = [positioned_brick]
            return True

    def remove_brick(self, position:tuple[int, int, int]) -> bool:
        """
        Attempt to remove a brick in the model at a specified position.
        
        Args:
            position (tuple[int, int, int]): The x, y and z coordinates, for the left, front, bottom corner, respectively
        
        Returns:
            bool: Whether the placement was succesful or not

        Raises:
            TypeError: If the inputs are invalid
        """
        # Verify the inputs
        if (not isinstance(position, tuple) and not isinstance(position, list)) or not isinstance(position[0], int) or not isinstance(position[1], int) or not isinstance(position[2], int):
            raise TypeError("position must contain the coordinates in (x,y,z) format (tuple[int]).")
        
        x,y,z = position
        if z in self.__layers:
            brick_count = len(self.__layers[z])
            for brick in range(brick_count):
                if self.__layers[z][brick]["position"] == (x,y):
                    if brick_count == 1:
                        self.__layers.pop(z)
                    else:
                        self.__layers[z].pop(brick)
                    return True
        return False

    def normalize(self) -> None:
        """
        Normalize the model to start from (0,0,0) in the bottom left corner.
        This will change the position of all bricks in the model.
        """
        # Check if the model is already normalized
        if self.is_empty or self.min == (0, 0, 0):
            return

        x_min, y_min, z_min = self.min
        for z in self.__layers.keys():
            for brick in self.__layers[z]:
                brick["position"] = (brick["position"][0] - x_min, brick["position"][1] - y_min)
        self.__layers = {z-z_min:self.__layers[z] for z in self.__layers.keys()}

    def __is_overlap(self, brick1:dict, brick2:dict) -> bool:
        """
        Check if two bricks overlap based on their size and position.

        Bricks must contain at least: {"size":(x,y), "position":(x,y)}
        """
        x_size1, y_size1 = brick1["size"]
        x_size2, y_size2 = brick2["size"]
        x1, y1 = brick1["position"]
        x2, y2 = brick2["position"]        

        if (x1 + x_size1 > x2 and x2 + x_size2 > x1 and
            y1 + y_size1 > y2 and y2 + y_size2 > y1):
            return True
        return False

    def __str__(self):
        result = ""
        # Sort layers from bottom to top
        for z in sorted(self.__layers.keys()):
            result += f"Layer {z}:\n"
            for brick in self.__layers[z]:
                brick_size = brick["size"]
                brick_position = brick["position"]
                result += f"  {'Support' if brick['support'] else 'Building'} brick ({brick_size[0]} x {brick_size[1]}) at: ({brick_position[0]}, {brick_position[1]}) \n"
        return result
