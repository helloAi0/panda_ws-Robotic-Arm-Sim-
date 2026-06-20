"""
perception.launch.py
Run AFTER gazebo.launch.py is running.
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    color_detector = Node(
        package='panda_perception',
        executable='color_detector',
        name='color_detector_node',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([color_detector])
