from setuptools import setup

package_name = 'panda_manipulation'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='helloAi0',
    maintainer_email='tahaudaipurwala68@gmail.com',
    description='Pick and place manipulation for Franka Panda',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'motion_test = panda_manipulation.motion_test:main',
        ],
    },
)
