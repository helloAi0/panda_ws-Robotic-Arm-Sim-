import os
import re
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node


def generate_launch_description():

    panda_description_pkg = get_package_share_directory('panda_description')
    panda_gazebo_pkg      = get_package_share_directory('panda_gazebo')

    xacro_file = os.path.join(
        panda_description_pkg, 'urdf', 'panda.urdf.xacro')
    result = subprocess.run(
        ['xacro', xacro_file, 'use_sim:=true', 'hand:=true'],
        capture_output=True, text=True, check=True
    )
    urdf_raw = result.stdout
    urdf_clean = re.sub(r'<\?xml[^?]*\?>', '', urdf_raw)
    urdf_clean = re.sub(r'<!--.*?-->', '', urdf_clean, flags=re.DOTALL)
    urdf_clean = re.sub(r'\s+', ' ', urdf_clean).strip()

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'robot_description': urdf_clean},
            {'use_sim_time': True}
        ]
    )

    # KEY FIX: Set GAZEBO_MODEL_DATABASE_URI to empty string
    # This prevents gzserver from trying to reach models.gazebosim.org
    # which hangs for 15+ minutes in Docker (no internet access to that host)
    gazebo_env = {
        'GAZEBO_MODEL_DATABASE_URI': '',
        'GAZEBO_RESOURCE_PATH': (
            '/root/panda_ws/install/panda_description/share:'
            '/root/panda_ws/install:'
            '/usr/share/gazebo-11'
        ),
        'GAZEBO_PLUGIN_PATH': (
            '/root/panda_ws/install/gazebo_ros2_control/lib:'
            '/opt/ros/humble/lib'
        ),
    }

    gzserver = ExecuteProcess(
        cmd=[
            'gzserver',
            os.path.join(panda_gazebo_pkg, 'worlds', 'sorting_world.world'),
            '-slibgazebo_ros_init.so',
            '-slibgazebo_ros_factory.so',
            '-slibgazebo_ros_force_system.so',
            '--verbose',
        ],
        additional_env=gazebo_env,
        output='screen',
    )

    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_panda',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'panda',
            '-x', '0.0', '-y', '0.0', '-z', '0.0',
        ],
        output='screen'
    )

    rviz_config = os.path.join(
        panda_description_pkg, 'rviz', 'panda_view.rviz')
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config] if os.path.exists(rviz_config) else [],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    jsb_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster',
                   '--controller-manager', '/controller_manager'],
        output='screen',
    )
    arm_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['panda_arm_controller',
                   '--controller-manager', '/controller_manager'],
        output='screen',
    )
    hand_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['panda_hand_controller',
                   '--controller-manager', '/controller_manager'],
        output='screen',
    )

    on_spawn_jsb = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot,
            on_exit=[jsb_spawner],
        )
    )
    on_jsb_arm = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=jsb_spawner,
            on_exit=[arm_spawner],
        )
    )
    on_arm_hand = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=arm_spawner,
            on_exit=[hand_spawner],
        )
    )

    return LaunchDescription([
        robot_state_publisher,
        gzserver,
        spawn_robot,
        rviz,
        on_spawn_jsb,
        on_jsb_arm,
        on_arm_hand,
    ])
