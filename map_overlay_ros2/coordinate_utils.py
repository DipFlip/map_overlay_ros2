"""Coordinate conversion utilities for map tiles and geographic coordinates."""

import math


def lat_lon_to_tile(lat, lon, zoom):
    """
    Convert latitude/longitude to tile coordinates at a given zoom level.

    Uses Web Mercator projection (EPSG:3857) tile numbering.

    Args:
        lat: Latitude in degrees (-85.05 to 85.05)
        lon: Longitude in degrees (-180 to 180)
        zoom: Zoom level (0-19)

    Returns:
        tuple: (tile_x, tile_y) integers
    """
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_lat_lon(x, y, zoom):
    """
    Convert tile coordinates to latitude/longitude (top-left corner of tile).

    Args:
        x: Tile X coordinate
        y: Tile Y coordinate
        zoom: Zoom level

    Returns:
        tuple: (lat, lon) in degrees
    """
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def meters_to_lat_lon_offset(lat, dx_m, dy_m):
    """
    Convert meter offsets to latitude/longitude offsets.

    Args:
        lat: Reference latitude in degrees
        dx_m: East-West offset in meters (positive = east)
        dy_m: North-South offset in meters (positive = north)

    Returns:
        tuple: (dlat, dlon) offsets in degrees
    """
    # Earth radius in meters
    R = 6378137.0

    # Coordinate offsets in radians
    dlat_rad = dy_m / R
    dlon_rad = dx_m / (R * math.cos(math.radians(lat)))

    # Convert to degrees
    dlat = math.degrees(dlat_rad)
    dlon = math.degrees(dlon_rad)

    return dlat, dlon


def calculate_bounding_box(center_lat, center_lon, width_m, height_m):
    """
    Calculate bounding box in lat/lon given a center point and dimensions in meters.

    Args:
        center_lat: Center latitude in degrees
        center_lon: Center longitude in degrees
        width_m: Width in meters
        height_m: Height in meters

    Returns:
        dict: {'min_lat', 'max_lat', 'min_lon', 'max_lon'}
    """
    # Calculate half-width and half-height offsets
    dlat, dlon = meters_to_lat_lon_offset(center_lat, width_m / 2.0, height_m / 2.0)

    return {
        'min_lat': center_lat - dlat,
        'max_lat': center_lat + dlat,
        'min_lon': center_lon - dlon,
        'max_lon': center_lon + dlon
    }


def calculate_optimal_zoom(width_m, image_size=1024, lat=0):
    """
    Determine the optimal zoom level for desired coverage.

    At the equator:
    - Zoom 0: One tile = 40,075,016 meters
    - Each zoom level doubles the resolution

    Args:
        width_m: Desired coverage width in meters
        image_size: Target image size in pixels
        lat: Latitude for scaling correction (closer to poles = smaller meters/pixel)

    Returns:
        int: Optimal zoom level (0-19)
    """
    # Meters per pixel at zoom 0 at equator
    meters_per_pixel_zoom0 = 156543.03392

    # Adjust for latitude (Web Mercator distortion)
    meters_per_pixel_zoom0 *= math.cos(math.radians(lat))

    # Target resolution
    target_meters_per_pixel = width_m / image_size

    # Calculate zoom level
    zoom = math.log2(meters_per_pixel_zoom0 / target_meters_per_pixel)

    # Clamp to valid range
    zoom = max(0, min(19, int(round(zoom))))

    return zoom


def get_tile_bounds(center_lat, center_lon, width_m, height_m, zoom, padding=1):
    """
    Calculate which tiles are needed to cover a geographic area.

    Args:
        center_lat: Center latitude in degrees
        center_lon: Center longitude in degrees
        width_m: Width in meters
        height_m: Height in meters
        zoom: Zoom level
        padding: Extra tiles to fetch on each side (ensures the GPS center
                 has enough canvas room for a properly centered crop)

    Returns:
        dict: {
            'min_tile_x': int,
            'max_tile_x': int,
            'min_tile_y': int,
            'max_tile_y': int,
            'zoom': int
        }
    """
    # Calculate bounding box
    bbox = calculate_bounding_box(center_lat, center_lon, width_m, height_m)

    # Convert corners to tile coordinates
    min_tile_x, max_tile_y = lat_lon_to_tile(bbox['min_lat'], bbox['min_lon'], zoom)
    max_tile_x, min_tile_y = lat_lon_to_tile(bbox['max_lat'], bbox['max_lon'], zoom)

    # Add padding tiles so the GPS center point always has enough canvas
    # on all sides for a properly centered crop (avoids clamping offset)
    return {
        'min_tile_x': min_tile_x - padding,
        'max_tile_x': max_tile_x + padding,
        'min_tile_y': min_tile_y - padding,
        'max_tile_y': max_tile_y + padding,
        'zoom': zoom
    }


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth.

    Args:
        lat1, lon1: First point in degrees
        lat2, lon2: Second point in degrees

    Returns:
        float: Distance in meters
    """
    R = 6378137.0  # Earth radius in meters

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat_rad = math.radians(lat2 - lat1)
    dlon_rad = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(dlat_rad / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(dlon_rad / 2) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    return distance
