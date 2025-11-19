from setuptools import setup

package_name = 'map_overlay_ros2'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'requests',
        'Pillow',
        'numpy',
    ],
    zip_safe=True,
    maintainer='LAMP Team',
    maintainer_email='dev@example.com',
    description='Satellite map imagery publisher for ROS2',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'map_overlay_node = map_overlay_ros2.map_overlay_node:main',
        ],
    },
)
