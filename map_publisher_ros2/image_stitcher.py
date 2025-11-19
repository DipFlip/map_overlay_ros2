"""Image stitching utilities for combining map tiles into a single image."""

from PIL import Image
import numpy as np


class ImageStitcher:
    """Stitch multiple map tiles into a single image."""

    def __init__(self, tile_size=256, logger=None):
        """
        Initialize the image stitcher.

        Args:
            tile_size: Size of individual tiles in pixels (typically 256)
            logger: Optional logger instance (ROS node logger)
        """
        self.tile_size = tile_size
        self.logger = logger

    def _log(self, message, level='info'):
        """Log a message using ROS logger if available."""
        if self.logger:
            if level == 'info':
                self.logger.info(message)
            elif level == 'warn':
                self.logger.warn(message)
            elif level == 'error':
                self.logger.error(message)
        else:
            print(f"[{level.upper()}] {message}")

    def stitch_tiles(self, tiles, tile_bounds, output_size=(1024, 1024)):
        """
        Stitch tiles into a single image and resize to output size.

        Args:
            tiles: Dict mapping (tile_x, tile_y) -> PIL.Image
            tile_bounds: Dict with min_tile_x, max_tile_x, min_tile_y, max_tile_y
            output_size: Tuple (width, height) for final output image

        Returns:
            PIL.Image: Stitched and resized image
        """
        min_x = tile_bounds['min_tile_x']
        max_x = tile_bounds['max_tile_x']
        min_y = tile_bounds['min_tile_y']
        max_y = tile_bounds['max_tile_y']

        # Calculate canvas size
        tiles_wide = max_x - min_x + 1
        tiles_high = max_y - min_y + 1
        canvas_width = tiles_wide * self.tile_size
        canvas_height = tiles_high * self.tile_size

        self._log(f"Creating canvas: {canvas_width}x{canvas_height} ({tiles_wide}x{tiles_high} tiles)")

        # Create blank canvas
        canvas = Image.new('RGB', (canvas_width, canvas_height), color=(200, 200, 200))

        # Place tiles on canvas
        placed_count = 0
        for (tile_x, tile_y), tile_img in tiles.items():
            # Calculate position on canvas
            canvas_x = (tile_x - min_x) * self.tile_size
            canvas_y = (tile_y - min_y) * self.tile_size

            # Paste tile
            try:
                # Ensure tile is RGB mode
                if tile_img.mode != 'RGB':
                    tile_img = tile_img.convert('RGB')

                canvas.paste(tile_img, (canvas_x, canvas_y))
                placed_count += 1
            except Exception as e:
                self._log(f"Failed to paste tile ({tile_x}, {tile_y}): {e}", level='warn')

        self._log(f"Placed {placed_count}/{len(tiles)} tiles on canvas")

        # Resize to output size
        if (canvas_width, canvas_height) != output_size:
            self._log(f"Resizing from {canvas_width}x{canvas_height} to {output_size[0]}x{output_size[1]}")
            # Use LANCZOS for high-quality resizing (compatible with older Pillow)
            try:
                canvas = canvas.resize(output_size, Image.Resampling.LANCZOS)
            except AttributeError:
                # Fallback for older Pillow versions (< 10.0.0)
                canvas = canvas.resize(output_size, Image.LANCZOS)

        return canvas

    def add_grid_overlay(self, image, grid_spacing_m, meters_per_pixel, color=(255, 0, 0), alpha=128):
        """
        Add a grid overlay to the image for reference.

        Args:
            image: PIL.Image to add grid to
            grid_spacing_m: Grid spacing in meters
            meters_per_pixel: Scale factor (meters per pixel)
            color: RGB tuple for grid color
            alpha: Alpha transparency (0-255)

        Returns:
            PIL.Image: Image with grid overlay
        """
        from PIL import ImageDraw

        # Create a transparent overlay
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        width, height = image.size
        grid_spacing_px = int(grid_spacing_m / meters_per_pixel)

        # Draw vertical lines
        for x in range(0, width, grid_spacing_px):
            draw.line([(x, 0), (x, height)], fill=color + (alpha,), width=1)

        # Draw horizontal lines
        for y in range(0, height, grid_spacing_px):
            draw.line([(0, y), (width, y)], fill=color + (alpha,), width=1)

        # Composite overlay onto image
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        return Image.alpha_composite(image, overlay)

    def add_center_marker(self, image, color=(255, 0, 0), size=10):
        """
        Add a center crosshair marker to the image.

        Args:
            image: PIL.Image to add marker to
            color: RGB tuple for marker color
            size: Size of crosshair in pixels

        Returns:
            PIL.Image: Image with center marker
        """
        from PIL import ImageDraw

        draw = ImageDraw.Draw(image)
        width, height = image.size
        cx, cy = width // 2, height // 2

        # Draw crosshair
        draw.line([(cx - size, cy), (cx + size, cy)], fill=color, width=2)
        draw.line([(cx, cy - size), (cx, cy + size)], fill=color, width=2)

        return image

    def image_to_numpy(self, image):
        """
        Convert PIL Image to numpy array (for OpenCV/ROS compatibility).

        Args:
            image: PIL.Image

        Returns:
            numpy.ndarray: Image as numpy array (RGB)
        """
        return np.array(image)

    def numpy_to_image(self, array):
        """
        Convert numpy array to PIL Image.

        Args:
            array: numpy.ndarray (RGB)

        Returns:
            PIL.Image
        """
        return Image.fromarray(array)
