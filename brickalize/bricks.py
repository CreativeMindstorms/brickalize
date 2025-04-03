# brickalize/bricks.py
"""
Defines the fundamental Brick object and a collection class, BrickSet.
"""

# No external libraries like numpy, open3d etc. are directly used by these two classes.
# Standard library imports might be needed for older Python versions for type hints,
# but for Python 3.9+ list, tuple, set, dict work directly.

class Brick:
    # Property for all bricks
    height = 1.2

    def __init__(self, d1:int, d2:int, is_support:bool = False):
        """
        Brick object
        
        Args:
            d1 (int): First dimension of the lego brick (length)
            d2 (int): Second dimension of the lego brick (width)
            is_support (bool): Whether the brick is a normal (model) or support brick (for lego printers)
        
        Raises:
            TypeError: if the variable types are invalid
            ValueError: if the dimensions are negative
        """
        # Verify that the inputs are valid
        self.__verify_inputs(d1, d2, is_support)

        # Store the parameters privately
        self.__length = max(d1, d2)
        self.__width = min(d1, d2)
        self.__is_support = is_support

    def __verify_inputs(self, d1, d2, is_support):
        if not (isinstance(d1, int) and isinstance(d2, int)):
            raise TypeError("Dimensions of Brick must be integers.")
        if d1 < 1 or d2 < 1:
            raise ValueError("Dimensions of Brick must be at least 1")
        if not isinstance(is_support, bool):
            raise TypeError("is_support for Brick must be a boolean")

    @property
    def length(self) -> int:
        """Biggest dimension of the Lego Brick (excluding height)."""
        return self.__length

    @property
    def width(self) -> int:
        """Smallest dimension of the Lego Brick (excluding height)."""
        return self.__width

    @property
    def orientations(self) -> list[tuple[int, int]]:
        """
        A list of all of the possible orientations that the brick can be in (1 or 2).

        Returns:
            list[tuple[int, int]]: The list of all possible orientations. These are tuples of x and y.
        """
        if self.__length != self.__width:
            return [(self.__length, self.__width), (self.__width, self.__length)]
        else:
            return [(self.__length, self.__width)]

    @property
    def is_support(self) -> bool:
        """Whether or not the brick type is a support or a building brick."""
        return self.__is_support

    def oriented(self, x_long:bool) -> tuple[tuple[int, int], bool]:
        """
        Get an oriented, 2D version of the brick.

        Args:
            x_long (bool): Whether the x-axis contains the length (largest dimension). 
                The y-axis will contain the other value (width).

        Returns:
            tuple: A tuple containing:
                - size (tuple[int, int]): The (x, y) size of the brick.
                - type (bool): True if it is a support, otherwise False.
        """

        if x_long: return ((self.length, self.width), self.is_support)
        else: return ((self.width, self.length), self.is_support)

    def __str__(self):
        if self.__is_support:
            return f"Support Brick ({self.__length} x {self.__width} x {Brick.height})"
        else:
            return f"Brick ({self.__length} x {self.__width} x {Brick.height})"

class BrickSet:
    def __init__(self, bricks:list[Brick]):
        """
        Creates a set of unique bricks.
        This class is an iterable, which iterates over all bricks, in all orientations

        Args:
            bricks (list[Brick]): A list of bricks

        Raises:
            TypeError: if bricks is not a list of Brick objects.
            ValueError: if there are no (non-support) building bricks in the list
        """

        # Verify bricks is a valid type
        self.__verify_inputs(bricks)

        # Use a set to store unique bricks
        unique_bricks = set()
        self.__building_bricks = []
        self.__support_bricks = []

        # Append unique bricks to the bricks property
        for brick in bricks:
            brick_tuple = (brick.length, brick.width, brick.is_support)
            if brick_tuple not in unique_bricks:
                unique_bricks.add(brick_tuple)
                if brick.is_support:
                    self.__support_bricks.append(brick)
                else:
                    self.__building_bricks.append(brick)

    @property
    def has_support(self) -> bool:
        """Whether or not the brickset includes support bricks"""
        return len(self.__support_bricks) > 0

    @property
    def building_brick_orientations(self) -> list[tuple[int, int]]:
        """
        A list of all of the possible orientations that all of the building bricks in the set can be in.

        Returns:
            list[tuple[int, int]]: The list of all possible orientations. These are tuples of x and y.
        """
        orientations = []
        for brick in self.__building_bricks:
            for orientation in brick.orientations:
                orientations.append(orientation)
        
        return orientations

    @property
    def support_brick_orientations(self) -> list[tuple[int, int]]:
        """
        A list of all of the possible orientations that all of the support bricks in the set can be in.

        Returns:
            list[tuple[int, int]]: The list of all possible orientations. These are tuples of x and y.
        """
        orientations = []
        for brick in self.__support_bricks:
            for orientation in brick.orientations:
                orientations.append(orientation)
        
        return orientations

    @property
    def building_bricks(self) -> list[Brick]:
        """List of all the building bricks."""
        return self.__building_bricks
    
    @property
    def support_bricks(self) -> list[Brick]:
        """List of all the support bricks."""
        return self.__support_bricks
    
    @property
    def bricks(self) -> list[Brick]:
        """List of all the bricks in the set, including both building and support bricks."""
        return self.__building_bricks + self.__support_bricks

    def get_building_bricks_by_dimension(self, dimension: int) -> set:
        """
        Get a set of all dimension by x bricks, where the set contains all complementary x
        
        Args:
            dimension (int): the dimension the bricks must have

        Returns:
            set[int]: A set containing the other dimension of the bricks that satisfy the dimension, sorted from largest to smallest
        """
        brick_set = set()
        for orientation in self.building_brick_orientations:
            if orientation[0] == dimension:
                brick_set.add(orientation[1])
        return sorted(brick_set, reverse=True)

    def get_building_brick_dimensions(self) -> set:
        """
        Get a set of all dimensions available with the bricks.

        Returns:
            set[int]: A set containing all dimensions of the bricks, sorted from largest to smallest
        """
        dimension_set = set()
        for brick in self.building_brick_orientations:
            for dimension in brick:
                dimension_set.add(dimension)
        return sorted(dimension_set, reverse=True)

    def get_support_bricks_by_dimension(self, dimension: int) -> set:
        """
        Get a set of all dimension by x bricks, where the set contains all complementary x
        
        Args:
            dimension (int): the dimension the bricks must have

        Returns:
            set[int]: A set containing the other dimension of the bricks that satisfy the dimension, sorted from largest to smallest
        """
        brick_set = set()
        for orientation in self.support_brick_orientations:
            if orientation[0] == dimension:
                brick_set.add(orientation[1])
        return sorted(brick_set, reverse=True)

    def get_support_brick_dimensions(self) -> set:
        """
        Get a set of all dimensions available with the bricks.

        Returns:
            set[int]: A set containing all dimensions of the bricks, sorted from largest to smallest
        """
        dimension_set = set()
        for brick in self.support_brick_orientations:
            for dimension in brick:
                dimension_set.add(dimension)
        return sorted(dimension_set, reverse=True)

    def __verify_inputs(self, bricks):
        if not isinstance(bricks, list):
            raise TypeError("bricks must be a list of Brick objects.")

        if not all(isinstance(brick, Brick) for brick in bricks):
            raise TypeError("bricks must contain only Brick objects.")
        
        for brick in bricks:
            if not brick.is_support:
                return
        raise ValueError("There must be at leat one building brick, that is not a support brick.")

    def __iter__(self):
        """
        yield each brick.
        First yields all of the building bricks.
        Then yields all of the support bricks.
        """
        for brick in self.__building_bricks:
            yield brick
        for brick in self.__support_bricks:
            yield brick

    def __str__(self):
        string = "Building bricks:"
        for brick in self.__building_bricks:
            string += "\n" + str(brick)
        if self.has_support:
            string += "\nSupport bricks:"
            for brick in self.__support_bricks:
                string += "\n" + str(brick)
        return string
