"""Tile fetcher for downloading satellite imagery from various providers."""

import os
import io
import hashlib
import requests
from PIL import Image


class TileFetcher:
    """Fetch and cache satellite tiles from map tile providers."""

    # Available tile providers
    PROVIDERS = {
        'esri': {
            'name': 'Esri World Imagery',
            'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'max_zoom': 19,
            'attribution': 'Esri, DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community',
            'tile_size': 256
        },
        'osm': {
            'name': 'OpenStreetMap',
            'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            'max_zoom': 19,
            'attribution': 'OpenStreetMap contributors',
            'tile_size': 256
        },
        'usgs': {
            'name': 'USGS Imagery',
            'url': 'https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',
            'max_zoom': 16,
            'attribution': 'USGS',
            'tile_size': 256
        }
    }

    def __init__(self, provider='esri', cache_dir='/tmp/map_tiles', logger=None):
        """
        Initialize the tile fetcher.

        Args:
            provider: Provider name ('esri', 'osm', 'usgs')
            cache_dir: Directory for caching tiles
            logger: Optional logger instance (ROS node logger)
        """
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Choose from {list(self.PROVIDERS.keys())}")

        self.provider = provider
        self.provider_config = self.PROVIDERS[provider]
        self.cache_dir = cache_dir
        self.logger = logger

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

        self._log(f"Initialized TileFetcher with provider: {self.provider_config['name']}")

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

    def _get_cache_path(self, z, x, y):
        """Generate cache file path for a tile."""
        # Create subdirectories for better organization
        zoom_dir = os.path.join(self.cache_dir, self.provider, str(z), str(x))
        os.makedirs(zoom_dir, exist_ok=True)
        return os.path.join(zoom_dir, f"{y}.png")

    def _get_tile_url(self, z, x, y):
        """Generate the URL for a specific tile."""
        url_template = self.provider_config['url']
        return url_template.format(z=z, x=x, y=y)

    def fetch_tile(self, z, x, y, use_cache=True):
        """
        Fetch a single tile, with optional caching.

        Args:
            z: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate
            use_cache: Whether to use cached tiles

        Returns:
            PIL.Image: The tile image, or None if fetch failed
        """
        cache_path = self._get_cache_path(z, x, y)

        # Check cache first
        if use_cache and os.path.exists(cache_path):
            try:
                img = Image.open(cache_path)
                self._log(f"Loaded tile ({z}/{x}/{y}) from cache", level='info')
                return img.copy()  # Return copy to avoid file handle issues
            except Exception as e:
                self._log(f"Failed to load cached tile ({z}/{x}/{y}): {e}", level='warn')
                # Continue to fetch from network

        # Fetch from provider
        url = self._get_tile_url(z, x, y)

        try:
            self._log(f"Fetching tile ({z}/{x}/{y}) from {url}", level='info')
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'MapPublisherROS2/1.0'
            })

            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))

                # Save to cache
                if use_cache:
                    try:
                        img.save(cache_path, 'PNG')
                        self._log(f"Cached tile ({z}/{x}/{y})", level='info')
                    except Exception as e:
                        self._log(f"Failed to cache tile ({z}/{x}/{y}): {e}", level='warn')

                return img
            else:
                self._log(f"Failed to fetch tile ({z}/{x}/{y}): HTTP {response.status_code}", level='error')
                return None

        except requests.exceptions.Timeout:
            self._log(f"Timeout fetching tile ({z}/{x}/{y})", level='error')
            return None
        except Exception as e:
            self._log(f"Error fetching tile ({z}/{x}/{y}): {e}", level='error')
            return None

    def fetch_tiles(self, tile_bounds):
        """
        Fetch multiple tiles covering a bounding box.

        Args:
            tile_bounds: Dict with keys: min_tile_x, max_tile_x, min_tile_y, max_tile_y, zoom

        Returns:
            dict: Map of (x, y) -> PIL.Image for successfully fetched tiles
        """
        z = tile_bounds['zoom']
        min_x = tile_bounds['min_tile_x']
        max_x = tile_bounds['max_tile_x']
        min_y = tile_bounds['min_tile_y']
        max_y = tile_bounds['max_tile_y']

        tiles = {}
        total_tiles = (max_x - min_x + 1) * (max_y - min_y + 1)

        self._log(f"Fetching {total_tiles} tiles at zoom {z}", level='info')

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                img = self.fetch_tile(z, x, y)
                if img:
                    tiles[(x, y)] = img
                else:
                    self._log(f"Skipping tile ({z}/{x}/{y}) due to fetch failure", level='warn')

        self._log(f"Successfully fetched {len(tiles)}/{total_tiles} tiles", level='info')

        return tiles

    def clear_cache(self):
        """Clear all cached tiles for this provider."""
        provider_cache_dir = os.path.join(self.cache_dir, self.provider)
        if os.path.exists(provider_cache_dir):
            import shutil
            shutil.rmtree(provider_cache_dir)
            self._log(f"Cleared cache for provider: {self.provider}", level='info')

    def get_provider_info(self):
        """Get information about the current provider."""
        return {
            'name': self.provider_config['name'],
            'max_zoom': self.provider_config['max_zoom'],
            'attribution': self.provider_config['attribution'],
            'tile_size': self.provider_config['tile_size']
        }
