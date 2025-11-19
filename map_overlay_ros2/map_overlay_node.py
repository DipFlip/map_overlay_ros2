"""
Map Publisher ROS2 Node

Subscribes to GPS data and publishes satellite imagery as a ROS2 Image message.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import json
import numpy as np

from .coordinate_utils import (
    calculate_optimal_zoom,
    get_tile_bounds,
    haversine_distance,
    calculate_bounding_box
)
from .tile_fetcher import TileFetcher
from .image_stitcher import ImageStitcher


class MapPublisherNode(Node):
    """ROS2 node that publishes satellite map imagery."""

    def __init__(self):
        super().__init__('map_overlay_node')

        # Declare parameters
        self.declare_parameter('coverage_meters', 500)
        self.declare_parameter('image_size', 1024)
        self.declare_parameter('tile_provider', 'esri')
        self.declare_parameter('update_on_movement', False)  # Changed: fetch only once at origin
        self.declare_parameter('movement_threshold_meters', 100.0)
        self.declare_parameter('cache_dir', '/tmp/map_tiles')
        self.declare_parameter('add_center_marker', True)
        self.declare_parameter('publish_rate_hz', 0.1)  # Once every 10 seconds
        self.declare_parameter('gps_topic', '/gps/fix')  # GPS topic to subscribe to
        self.declare_parameter('fetch_once_at_origin', True)  # New: only fetch map once

        # Get parameters
        self.coverage_meters = self.get_parameter('coverage_meters').value
        self.image_size = self.get_parameter('image_size').value
        self.tile_provider = self.get_parameter('tile_provider').value
        self.update_on_movement = self.get_parameter('update_on_movement').value
        self.movement_threshold = self.get_parameter('movement_threshold_meters').value
        self.cache_dir = self.get_parameter('cache_dir').value
        self.add_center_marker = self.get_parameter('add_center_marker').value
        self.publish_rate = self.get_parameter('publish_rate_hz').value
        self.gps_topic = self.get_parameter('gps_topic').value
        self.fetch_once_at_origin = self.get_parameter('fetch_once_at_origin').value

        # Initialize utilities
        self.cv_bridge = CvBridge()
        self.tile_fetcher = TileFetcher(
            provider=self.tile_provider,
            cache_dir=self.cache_dir,
            logger=self.get_logger()
        )
        self.image_stitcher = ImageStitcher(logger=self.get_logger())

        # State variables
        self.center_lat = None
        self.center_lon = None
        self.last_published_position = None
        self.last_published_image = None
        self.map_metadata = None
        self.map_fetched = False  # Track if we've fetched the origin map

        # Subscribers
        self.gps_sub = self.create_subscription(
            NavSatFix,
            self.gps_topic,
            self.gps_callback,
            10
        )

        # Publishers
        self.image_pub = self.create_publisher(
            Image,
            '/map_overlay/satellite_image',
            10
        )
        self.metadata_pub = self.create_publisher(
            String,
            '/map_overlay/map_metadata',
            10
        )

        # Timer for periodic publishing (even if GPS hasn't moved)
        self.publish_timer = self.create_timer(
            1.0 / self.publish_rate,
            self.publish_timer_callback
        )

        self.get_logger().info('=' * 60)
        self.get_logger().info('Map Publisher Node Initialized')
        self.get_logger().info(f'  Provider: {self.tile_provider}')
        self.get_logger().info(f'  Coverage: {self.coverage_meters}m')
        self.get_logger().info(f'  Image Size: {self.image_size}x{self.image_size}')
        self.get_logger().info(f'  Fetch once at origin: {self.fetch_once_at_origin}')
        self.get_logger().info(f'  Update on movement: {self.update_on_movement}')
        self.get_logger().info(f'  Movement threshold: {self.movement_threshold}m')
        self.get_logger().info(f'  Publish rate: {self.publish_rate} Hz')
        self.get_logger().info('=' * 60)

    def gps_callback(self, msg):
        """Handle incoming GPS fix messages."""
        # Check for valid fix
        if msg.status.status < 0:
            self.get_logger().warn('No GPS fix, skipping map update')
            return

        lat = msg.latitude
        lon = msg.longitude

        # Check if position is valid
        if lat == 0.0 and lon == 0.0:
            self.get_logger().warn('Invalid GPS position (0, 0), skipping')
            return

        # Update center position
        self.center_lat = lat
        self.center_lon = lon

        # Check if we should fetch new map
        if self.should_update_map(lat, lon):
            self.fetch_and_publish_map(lat, lon)

    def should_update_map(self, lat, lon):
        """Determine if map needs updating based on movement."""
        # If fetch_once_at_origin is enabled, only fetch once
        if self.fetch_once_at_origin:
            if self.map_fetched:
                return False
            else:
                return True

        # Otherwise use the original movement-based logic
        if self.last_published_position is None:
            return True

        if not self.update_on_movement:
            return False

        # Calculate distance moved
        last_lat, last_lon = self.last_published_position
        dist = haversine_distance(last_lat, last_lon, lat, lon)

        if dist > self.movement_threshold:
            self.get_logger().info(f'Moved {dist:.1f}m, updating map')
            return True

        return False

    def fetch_and_publish_map(self, lat, lon):
        """Fetch satellite tiles and publish stitched image."""
        try:
            # Calculate optimal zoom level
            zoom = calculate_optimal_zoom(
                self.coverage_meters,
                self.image_size,
                lat
            )

            self.get_logger().info(f'Fetching map for ({lat:.6f}, {lon:.6f}) at zoom {zoom}')

            # Calculate which tiles to fetch
            tile_bounds = get_tile_bounds(
                lat, lon,
                self.coverage_meters,
                self.coverage_meters,
                zoom
            )

            # Fetch tiles
            tiles = self.tile_fetcher.fetch_tiles(tile_bounds)

            if not tiles:
                self.get_logger().error('No tiles fetched, cannot create map')
                return

            # Stitch tiles into single image
            stitched_image = self.image_stitcher.stitch_tiles(
                tiles,
                tile_bounds,
                (self.image_size, self.image_size)
            )

            # Add center marker if requested
            if self.add_center_marker:
                stitched_image = self.image_stitcher.add_center_marker(
                    stitched_image,
                    color=(255, 0, 0),
                    size=10
                )

            # Convert PIL Image to numpy array
            img_array = self.image_stitcher.image_to_numpy(stitched_image)

            # Convert RGB to BGR for OpenCV/ROS convention
            img_array_bgr = img_array[:, :, ::-1]

            # Store for periodic publishing
            self.last_published_image = img_array_bgr
            self.last_published_position = (lat, lon)
            self.map_fetched = True  # Mark that we've fetched the map

            # Create metadata
            bbox = calculate_bounding_box(
                lat, lon,
                self.coverage_meters,
                self.coverage_meters
            )

            self.map_metadata = {
                'center_lat': lat,
                'center_lon': lon,
                'coverage_meters': self.coverage_meters,
                'image_size': self.image_size,
                'zoom': zoom,
                'bbox': bbox,
                'provider': self.tile_provider
            }

            # Publish
            self.publish_image_and_metadata()

            if self.fetch_once_at_origin:
                self.get_logger().info(f'Origin satellite map fetched and will be published at ({lat:.6f}, {lon:.6f}) - no further updates')
            else:
                self.get_logger().info(f'Successfully published map for ({lat:.6f}, {lon:.6f})')

        except Exception as e:
            self.get_logger().error(f'Failed to fetch and publish map: {e}')
            import traceback
            self.get_logger().error(traceback.format_exc())

    def publish_timer_callback(self):
        """Periodically re-publish the last image (for new subscribers)."""
        if self.last_published_image is not None:
            self.publish_image_and_metadata()

    def publish_image_and_metadata(self):
        """Publish the stored image and metadata."""
        if self.last_published_image is None:
            return

        try:
            # Convert numpy array to ROS Image message
            ros_image = self.cv_bridge.cv2_to_imgmsg(
                self.last_published_image,
                encoding='bgr8'
            )

            # Publish image
            self.image_pub.publish(ros_image)

            # Publish metadata
            if self.map_metadata:
                metadata_msg = String()
                metadata_msg.data = json.dumps(self.map_metadata)
                self.metadata_pub.publish(metadata_msg)

        except Exception as e:
            self.get_logger().error(f'Failed to publish image/metadata: {e}')


def main(args=None):
    """Main entry point for the node."""
    rclpy.init(args=args)

    node = MapPublisherNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
