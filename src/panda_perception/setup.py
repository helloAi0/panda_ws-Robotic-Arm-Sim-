from setuptools import setup

package_name = 'panda_perception'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
            ['launch/perception.launch.py']),
        ('share/' + package_name + '/config',
            ['config/color_thresholds.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='helloAi0',
    maintainer_email='tahaudaipurwala68@gmail.com',
    description='OpenCV color detection for Panda sorting robot',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'color_detector = panda_perception.color_detector:main',
            'scene_markers = panda_perception.scene_markers:main',
        ],
    },
)
