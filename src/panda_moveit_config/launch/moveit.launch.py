import os
import re
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    panda_description_pkg = get_package_share_directory('panda_description')
    panda_moveit_pkg      = get_package_share_directory('panda_moveit_config')

    # Process XACRO
    xacro_file = os.path.join(panda_description_pkg, 'urdf', 'panda.urdf.xacro')
    result = subprocess.run(
        ['xacro', xacro_file, 'use_sim:=true', 'hand:=true'],
        capture_output=True, text=True, check=True
    )
    urdf_raw   = result.stdout
    urdf_clean = re.sub(r'<\?xml[^?]*\?>', '', urdf_raw)
    urdf_clean = re.sub(r'<!--.*?-->', '', urdf_clean, flags=re.DOTALL)
    urdf_clean = re.sub(r'\s+', ' ', urdf_clean).strip()

    # Load SRDF
    srdf_path = os.path.join(panda_moveit_pkg, 'config', 'panda.srdf')
    with open(srdf_path, 'r') as f:
        srdf_content = f.read()

    move_group = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        name='move_group',
        output='screen',
        parameters=[
            # Robot description
            {'robot_description': urdf_clean},
            {'robot_description_semantic': srdf_content},
            {'use_sim_time': True},
            {'publish_robot_description_semantic': True},

            # ── Planning plugin ───────────────────────────────────────────
            # Must be set directly — not via YAML file loading
            {'planning_plugin': 'ompl_interface/OMPLPlanner'},
            {'request_adapters': ' '.join([
                'default_planner_request_adapters/AddTimeOptimalParameterization',
                'default_planner_request_adapters/FixWorkspaceBounds',
                'default_planner_request_adapters/FixStartStateBounds',
                'default_planner_request_adapters/FixStartStateCollision',
            ])},
            {'start_state_max_bounds_error': 0.1},

            # ── Kinematics ────────────────────────────────────────────────
            # Keys must match group names exactly
            {'panda_arm.kinematics_solver':
                'kdl_kinematics_plugin/KDLKinematicsPlugin'},
            {'panda_arm.kinematics_solver_search_resolution': 0.005},
            {'panda_arm.kinematics_solver_timeout': 0.005},
            {'panda_arm.kinematics_solver_attempts': 3},

            # ── Controller manager ────────────────────────────────────────
            {'moveit_controller_manager':
                'moveit_simple_controller_manager/MoveItSimpleControllerManager'},
            {'moveit_simple_controller_manager.controller_names': [
                'panda_arm_controller',
                'panda_hand_controller',
            ]},
            # Arm controller
            {'moveit_simple_controller_manager.panda_arm_controller.type':
                'FollowJointTrajectory'},
            {'moveit_simple_controller_manager.panda_arm_controller.action_ns':
                'follow_joint_trajectory'},
            {'moveit_simple_controller_manager.panda_arm_controller.default': True},
            {'moveit_simple_controller_manager.panda_arm_controller.joints': [
                'panda_joint1', 'panda_joint2', 'panda_joint3', 'panda_joint4',
                'panda_joint5', 'panda_joint6', 'panda_joint7',
            ]},
            # Hand controller
            {'moveit_simple_controller_manager.panda_hand_controller.type':
                'FollowJointTrajectory'},
            {'moveit_simple_controller_manager.panda_hand_controller.action_ns':
                'follow_joint_trajectory'},
            {'moveit_simple_controller_manager.panda_hand_controller.default': True},
            {'moveit_simple_controller_manager.panda_hand_controller.joints': [
                'panda_finger_joint1', 'panda_finger_joint2',
            ]},

            # ── Trajectory execution ──────────────────────────────────────
            {'trajectory_execution.allowed_execution_duration_scaling': 1.2},
            {'trajectory_execution.allowed_goal_duration_margin': 0.5},
            {'trajectory_execution.allowed_start_tolerance': 0.01},

            # ── Planning scene ────────────────────────────────────────────
            {'planning_scene_monitor_options.publish_planning_scene': True},
            {'planning_scene_monitor_options.publish_geometry_updates': True},
            {'planning_scene_monitor_options.publish_state_updates': True},
            {'planning_scene_monitor_options.publish_transforms_updates': True},
        ],
    )

    return LaunchDescription([move_group])
