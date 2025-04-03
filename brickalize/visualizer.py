# brickalize/visualizer.py
"""
Provides the BrickModelVisualizer class for creating visual representations
of BrickModel objects, including 3D meshes and 2D layer images.
"""

import open3d as o3d # For 3D models and visualization
import numpy as np # Arrays
import cv2  # OpenCV for image generation
from tqdm import tqdm # For Progress bar during long operations
import math # Needed for checking directory paths in save_as_images

# Import necessary classes from other modules within the package
from .bricks import Brick         # For default height and potentially type hints
from .model import BrickModel     # To process BrickModel objects


class BrickModelVisualizer:
    # Create materials for the bricks and support bricks
    brick_mat = o3d.visualization.rendering.MaterialRecord()
    brick_mat.shader = 'defaultLit'
    brick_mat.base_color = [1.0,1.0,0.0,1.0] # rgba

    support_mat = o3d.visualization.rendering.MaterialRecord()
    support_mat.shader = 'defaultLitTransparency'
    support_mat.base_color = [1.0,0.0,0.0,0.7] # rgba

    @staticmethod
    def draw_brick(position: tuple, size: tuple):
        """
        Create a solid box in Open3D.

        Args:
            position (tuple): (x, y, z) coordinates representing the center of the box.
            size (tuple): (l, w, h) dimensions of the box.

        Returns:
            open3d.geometry.TriangleMesh: Open3D mesh object representing the box.
        """
        l, w, h = size
        x, y, z = position
        
        # Create a box mesh
        box = o3d.geometry.TriangleMesh.create_box(width=w, height=l, depth=h)
        
        # Move the box to the correct position (Open3D creates boxes at origin by default)
        box.translate(np.array([x,y,z]))
        box.compute_triangle_normals()
        
        return box
    
    @classmethod
    def draw_model_individual_bricks(cls, brick_model: BrickModel) -> list:
        """
        Draw multiple bricks in Open3D with transparency.

        Args:
            brick_model (BrickModel): A BrickModel instance from this module.

        Returns:
            list: A mesh list containing all the meshes (dictionaries containing 'name', 'geometry' and 'material' as keys)
        """
        mesh_list = []
        
        for z in sorted(brick_model.layers.keys()):
            for brick in brick_model.layers[z]:
                brick_size = (brick["size"][1], brick["size"][0], brick_model.layer_height)
                brick_position = (brick["position"][0], brick["position"][1], z * brick_model.layer_height)
                box = cls.draw_brick(brick_position, brick_size)
                if brick["support"]:
                    mesh_list.append({'name': str(brick_position), 'geometry': box, 'material': cls.support_mat})
                else:
                    mesh_list.append({'name': str(brick_position), 'geometry': box, 'material': cls.brick_mat})
        return mesh_list

    @classmethod
    def draw_model(cls, voxel_array: np.ndarray, support_array: np.ndarray = None, voxel_height: float = Brick.height) -> list:
        """
        Draw multiple bricks in Open3D with transparency.

        Args:
            voxel_array (np.ndarray): A 3D binary array [z,x,y] with the True values being occupied spaces with building bricks of the model.
            support_array (np.ndarray, optional): A 3D binary array [z,x,y] with the True values being occupied spaces with support bricks of the model. (standard = None)
            voxel_height (float): The relative height of the voxels (the width and depth are 1)

        Returns:
            list: A mesh list containing 1 or 2 meshes (dictionaries containing 'name', 'geometry' and 'material' as keys)
        """
        mesh_list = []

        # Model
        mesh = cls.generate_mesh_from_voxels(voxel_array, voxel_height=voxel_height)
        mesh_list.append({'name': "model", 'geometry': mesh, 'material': cls.brick_mat})

        # Optional support
        if support_array is not None:
            mesh = cls.generate_mesh_from_voxels(support_array, voxel_height=voxel_height)
            mesh_list.append({'name': "support", 'geometry': mesh, 'material': cls.support_mat})

        return mesh_list

    @staticmethod
    def generate_mesh_from_voxels(voxel_array: np.ndarray, voxel_height: float = Brick.height) -> o3d.geometry.TriangleMesh:
        """
        Generates a mesh from a 3D binary array containing all exposed surfaces.

        Args:
            voxel_array (np.ndarray): A 3D binary array with the True values being occupied spaces of the model.
            voxel_height (float): The relative height of the voxels (the width and depth are 1)
        
        Returns:
            open3d.geometry.TriangleMesh: Open3D mesh object representing the model.
        """
        # Get the shape of the voxel grid
        z_dim, x_dim, y_dim = voxel_array.shape
        
        # Initialize the list of vertices and faces
        vertices = []
        faces = []

        # Directions for checking neighboring voxels (in the order of +x, -x, +y, -y, +z, -z)
        directions = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        
        # Initialize a counter for unique vertices
        for z in range(z_dim):
            for x in range(x_dim):
                for y in range(y_dim):
                    if voxel_array[z, x, y]:  # If voxel is filled (True)
                        # Check each face of the voxel (6 directions)
                        for direction in directions:
                            dz, dx, dy = direction
                            nz, nx, ny = z + dz, x + dx, y + dy
                            
                            # Check if the neighbor is out of bounds or empty (False)
                            if (nz < 0 or nz >= z_dim or nx < 0 or nx >= x_dim or ny < 0 or ny >= y_dim or not voxel_array[nz, nx, ny]):
                                # This face is exposed, add it
                                # Define the 4 corners of the exposed face
                                base_vertex = np.array([x, y, z * voxel_height])  # Scale by voxel_size
                                if dz == 1:
                                    # +z face
                                    face_vertices = [base_vertex + np.array([0, 0, voxel_height]),
                                                    base_vertex + np.array([1, 0, voxel_height]),
                                                    base_vertex + np.array([1, 1, voxel_height]),
                                                    base_vertex + np.array([0, 1, voxel_height])]
                                elif dz == -1:
                                    # -z face
                                    face_vertices = [base_vertex + np.array([0, 0, 0]),
                                                    base_vertex + np.array([0, 1, 0]),
                                                    base_vertex + np.array([1, 1, 0]),
                                                    base_vertex + np.array([1, 0, 0])]
                                elif dx == 1:
                                    # +x face
                                    face_vertices = [base_vertex + np.array([1, 1, voxel_height]),
                                                    base_vertex + np.array([1, 0, voxel_height]),
                                                    base_vertex + np.array([1, 0, 0]),
                                                    base_vertex + np.array([1, 1, 0])]
                                elif dx == -1:
                                    # -x face
                                    face_vertices = [base_vertex + np.array([0, 1, voxel_height]),
                                                    base_vertex + np.array([0, 1, 0]),
                                                    base_vertex + np.array([0, 0, 0]),
                                                    base_vertex + np.array([0, 0, voxel_height])]
                                elif dy == 1:
                                    # +y face
                                    face_vertices = [base_vertex + np.array([1, 1, voxel_height]),
                                                    base_vertex + np.array([1, 1, 0]),
                                                    base_vertex + np.array([0, 1, 0]),
                                                    base_vertex + np.array([0, 1, voxel_height])]
                                elif dy == -1:
                                    # -y face
                                    face_vertices = [base_vertex + np.array([0, 0, 0]),
                                                    base_vertex + np.array([1, 0, 0]),
                                                    base_vertex + np.array([1, 0, voxel_height]),
                                                    base_vertex + np.array([0, 0, voxel_height])]
                                
                                # Add the face vertices to the list of vertices
                                for v in face_vertices:
                                    if v.tolist() not in vertices:
                                        vertices.append(v.tolist())
                                
                                # Create faces using the order of the vertices (Counter-clockwise)
                                v0 = vertices.index(face_vertices[0].tolist())
                                v1 = vertices.index(face_vertices[1].tolist())
                                v2 = vertices.index(face_vertices[2].tolist())
                                v3 = vertices.index(face_vertices[3].tolist())
                                
                                faces.append([v0, v1, v2])
                                faces.append([v0, v2, v3])
        
        # Create the Open3D TriangleMesh
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        mesh.triangles = o3d.utility.Vector3iVector(faces)
        
        # Compute normals for the mesh (after ensuring correct face orientation)
        mesh.compute_vertex_normals()

        return mesh
    
    @staticmethod
    def show_model(mesh_list: list):
        """
        Display a mesh list in an interactive 3D renderer using open3D

        Args:
            mesh_list (list): A mesh list containing meshes (dictionaries containing 'name', 'geometry' and 'material' as keys)
        """
        o3d.visualization.draw([box for box in mesh_list], show_skybox = False, ibl_intensity = 50000.0)

    @staticmethod
    def save_model(mesh_list: list, file_path: str) -> bool:
        """
        Save the model to an STL file.

        Args:
            mesh_list (list): List of Open3D mesh objects to be saved.
            file_path (str): Path to the output .stl file.

        Returns:
            bool: True if the file was saved successfully, False otherwise.
        """
        try:
            combined_mesh = o3d.geometry.TriangleMesh()
            for item in mesh_list:
                combined_mesh += item['geometry']
            o3d.io.write_triangle_mesh(file_path, combined_mesh)
            return True
        except:
            return False

    @classmethod
    def save_as_images(
        cls,
        brick_model: BrickModel,
        dir_path: str,
        brick_color: tuple = (0, 255, 255),
        support_color: tuple = (200, 200, 255),
        add_lego_overlay: bool = True,
        show_ghost_layer: bool = False,
        pixels_per_stud: int = 20,
        line_thickness: float = 0.05
    ):
        """
        Convert the model to images using Open3D.

        Args:
            brick_model (BrickModel): A BrickModel instance from this module.
            dir_path (str): Path to the directory where images will be saved.
            brick_color (tuple, optional): BGR color for normal bricks. Defaults to (0, 255, 255).
            support_color (tuple, optional): BGR color for support bricks. Defaults to (200, 200, 255).
            add_lego_overlay (bool, optional): Whether to add a shadow overlay to the images 
                (requires a minimum `pixels_per_stud` of 10). Defaults to True.
            show_ghost_layer (bool, optional): Whether to show a semi-transparent layer below the
                current layer, representing the lower layer. Defaults to False.
            pixels_per_stud (int, optional): Number of pixels per stud. Defaults to 20.
            line_thickness (float, optional): Thickness of the lines in the image relative to 
                the size of a stud. Defaults to 0.05.
        """
        empty = np.full(([brick_model.size[1] * pixels_per_stud, brick_model.size[0] * pixels_per_stud, 3]), 255, dtype=np.uint8)
        if show_ghost_layer: ghost_layer = np.copy(empty)
        if add_lego_overlay: shadow_img = cls.__generate_lego_shadow(pixels_per_stud)

        for z, layer in tqdm(sorted(brick_model.layers.items()), desc="Creating images..."):
            if show_ghost_layer:
                image = np.copy(ghost_layer)
                ghost_layer = np.copy(empty)
            else: image = np.copy(empty)
            for b in layer:
                w, l = b["size"]
                x = b["position"][0] - brick_model.min[0]
                y = brick_model.size[1] - b["position"][1] - l # Flip y-axis
                
                # Support bricks
                if b["support"]:
                    color = support_color
                    outline_color = tuple(c*0.8 for c in support_color)
                    if show_ghost_layer:
                        transparent_color = tuple(c+(255-c)//2 for c in color)
                
                # Normal bricks
                else:
                    color = brick_color
                    outline_color = tuple(c*0.8 for c in brick_color)
                    if show_ghost_layer:
                        transparent_color = tuple(c+(255-c)//1.5 for c in color)

                # fill
                cv2.rectangle(image, (x * pixels_per_stud, y * pixels_per_stud), ((x + w) * pixels_per_stud, (y + l) * pixels_per_stud), color, -1)
                if show_ghost_layer: cv2.rectangle(ghost_layer, (x * pixels_per_stud, y * pixels_per_stud), ((x + w) * pixels_per_stud, (y + l) * pixels_per_stud), transparent_color, -1)
            
                # outline
                if pixels_per_stud > 3:
                    cv2.rectangle(image, (x * pixels_per_stud, y * pixels_per_stud), ((x + w) * pixels_per_stud, (y + l) * pixels_per_stud), outline_color, math.ceil(line_thickness * pixels_per_stud))
                
                if pixels_per_stud > 9 and add_lego_overlay:
                    for i in range(w):
                        for j in range(l):
                            image = cls.__apply_shadow_with_multiply(image, shadow_img, (x+i) * pixels_per_stud, (y+j) * pixels_per_stud)
            cv2.imwrite(f"{dir_path}/layer_{z}.png", image)

    @staticmethod
    def __generate_lego_shadow(size) -> np.ndarray:
        """
        Creates a square image with a half-circle shadow effect.
        
        Args:
            size (int): Width and height of the output image (square).

        Returns:
            numpy.ndarray: A grayscale image with the shadow effect.
        """
        
        scaler = 0.6  # Shadow width spans 60% of the image width
        shadow_width = int(size * scaler)  # Shadow diameter based on scaler
        shadow_thickness = max(1, shadow_width // 10)  # Define thickness dynamically
        small_shadow_thickness = max(1, shadow_width // 14)  # Define thickness dynamically
        smaller_shadow_thickness = max(1, shadow_width // 16)  # Define thickness dynamically
        # Create a white square canvas
        img = np.ones((size, size), dtype=np.uint8) * 255

        # Define shadow position (bottom half-circle edge)
        center = (size // 2, size // 2)  # Slightly below center
        radius = shadow_width // 2  # Shadow spans the given width

        # Draw half-circles with various thickness and colors (black shadow)
        cv2.ellipse(img, center, (radius, radius), 0, 0, 180, 220, smaller_shadow_thickness)
        cv2.ellipse(img, center, (radius, radius), 0, 20, 160, 180, smaller_shadow_thickness)
        cv2.ellipse(img, center, (radius, radius), 0, 40, 140, 150, small_shadow_thickness)
        cv2.ellipse(img, center, (radius, radius), 0, 60, 120, 150, shadow_thickness)
        cv2.ellipse(img, center, (radius, radius), 0, 80, 100, 127, shadow_thickness)

        # Only blur if the image is large enough
        if size > 16:
            # Ensure blur size is a positive odd number
            blur_size = max(3, (shadow_width // 5) | 1)  # Must be odd
            img = cv2.GaussianBlur(img, (blur_size, blur_size), 0)
        
        # Convert shadow to RGBA
        shadow_rgba = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        shadow_float = shadow_rgba.astype(np.float32) / 255.0

        return shadow_float

    @staticmethod
    def __apply_shadow_with_multiply(image, shadow, x, y) -> np.ndarray:
        """
        Apply a shadow to a BGR image at the given (x, y) position using blend_modes.multiply.

        Args:
            image (numpy.ndarray): Background image (uint8, shape HxWx3).
            shadow (numpy.ndarray): Grayscale shadow image (uint8, shape SxS).
            x (int): X-coordinate of the top-left position to place the shadow.
            y (int): Y-coordinate of the top-left position to place the shadow.

        Returns:
            numpy.ndarray: The blended image (BGR, uint8).
        """

        # Convert images to float32 (range 0-1) for blending
        image_float = image.astype(np.float32) / 255.0

        # Create an overlay of the same size as the image
        overlay = np.ones_like(image, dtype=np.float32)

        # Place the shadow into the overlay at (x, y)
        h, w = shadow.shape[:2]
        try:
            overlay[y:y+h, x:x+w] = shadow
        except:
            # cv2.imshow("show", image_float)
            # cv2.imshow("show a", overlay)
            # cv2.waitKey(0)
            pass
        # Apply multiply blending
        blended = image_float*overlay

        # Convert back to uint8
        blended = (blended * 255).astype(np.uint8)

        return blended
