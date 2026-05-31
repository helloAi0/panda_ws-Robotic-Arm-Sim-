#!/usr/bin/env python3
"""
motion_test.py

First motion test for the Franka Panda arm using MoveIt2.
This node commands the arm to move to specific poses.

Run AFTER:
  Terminal 1: ros2 launch panda_gazebo gazebo.launch.py
  Terminal 2: ros2 launch panda_moveit_config moveit.launch.py
  Terminal 3: ros2 run panda_manipulation motion_test
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest,
    WorkspaceParameters,
    RobotState,
    Constraints,
    JointConstraint,
    MoveItErrorCodes,
)
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Vector3


class MotionTestNode(Node):

    def __init__(self):
        super().__init__('motion_test_node')
        self.get_logger().info('Motion Test Node starting...')

        # Action client — talks to move_group's MoveAction server
        self._action_client = ActionClient(
            self,
            MoveGroup,
            '/move_group'
        )

        # Store current joint states
        self._current_joint_states = None
        self._joint_state_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self._joint_state_callback,
            10
        )

        # Wait for action server
        self.get_logger().info('Waiting for move_group action server...')
        self._action_client.wait_for_server()
        self.get_logger().info('move_group action server found!')

        # Wait for first joint states
        self.get_logger().info('Waiting for joint states...')
        while self._current_joint_states is None:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info('Joint states received!')

        # Run test sequence
        self.run_motion_sequence()

    def _joint_state_callback(self, msg):
        self._current_joint_states = msg

    def move_to_joint_angles(self, joint_positions: dict, description: str):
        """
        Command the arm to move to specific joint angles.

        joint_positions: dict of {joint_name: angle_radians}
        description: human-readable label for this motion
        """
        self.get_logger().info(f'Planning motion: {description}')

        # Build the goal
        goal = MoveGroup.Goal()

        # ── Motion plan request ───────────────────────────────────────────
        request = MotionPlanRequest()
        request.group_name = 'panda_arm'  # Must match SRDF group name
        request.num_planning_attempts = 5
        request.allowed_planning_time = 5.0  # seconds
        request.max_velocity_scaling_factor = 0.3   # 30% of max speed (safe)
        request.max_acceleration_scaling_factor = 0.3

        # ── Workspace bounds ──────────────────────────────────────────────
        # Tell planner the volume to work in (meters)
        workspace = WorkspaceParameters()
        workspace.header.frame_id = 'panda_link0'
        workspace.min_corner = Vector3(x=-1.0, y=-1.0, z=-1.0)
        workspace.max_corner = Vector3(x=1.0,  y=1.0,  z=1.0)
        request.workspace_parameters = workspace

        # ── Start state = current state ───────────────────────────────────
        # Tell MoveIt where the arm is RIGHT NOW
        start_state = RobotState()
        start_state.joint_state = self._current_joint_states
        request.start_state = start_state

        # ── Goal constraints = target joint angles ────────────────────────
        # Each joint gets a JointConstraint specifying target angle
        joint_constraints = []
        for joint_name, position in joint_positions.items():
            constraint = JointConstraint()
            constraint.joint_name = joint_name
            constraint.position = position
            constraint.tolerance_above = 0.05  # radians tolerance
            constraint.tolerance_below = 0.05
            constraint.weight = 1.0
            joint_constraints.append(constraint)

        goal_constraints = Constraints()
        goal_constraints.joint_constraints = joint_constraints
        request.goal_constraints = [goal_constraints]

        goal.request = request
        goal.planning_options.plan_only = False       # plan AND execute
        goal.planning_options.replan = True
        goal.planning_options.replan_attempts = 3

        # ── Send goal ────────────────────────────────────────────────────
        self.get_logger().info(f'Sending goal: {description}')
        send_goal_future = self._action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_goal_future)

        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected!')
            return False

        self.get_logger().info('Goal accepted, executing...')

        # Wait for result
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result().result
        error_code = result.error_code.val

        if error_code == MoveItErrorCodes.SUCCESS:
            self.get_logger().info(f'SUCCESS: {description}')
            return True
        else:
            self.get_logger().error(
                f'FAILED: {description} — error code: {error_code}')
            return False

    def run_motion_sequence(self):
        """Execute a sequence of test motions."""

        self.get_logger().info('=' * 50)
        self.get_logger().info('STARTING MOTION TEST SEQUENCE')
        self.get_logger().info('=' * 50)

        # ── Motion 1: Move to extended position ──────────────────────────
        # Arm stretched upward — tests full range
        success = self.move_to_joint_angles(
            {
                'panda_joint1': 0.0,
                'panda_joint2': -0.3,
                'panda_joint3': 0.0,
                'panda_joint4': -1.5,
                'panda_joint5': 0.0,
                'panda_joint6': 1.2,
                'panda_joint7': 0.785,
            },
            'Move to extended position'
        )

        if not success:
            self.get_logger().error('First motion failed. Stopping.')
            return

        # Wait 2 seconds between motions
        import time
        time.sleep(2.0)

        # ── Motion 2: Move to ready/home position ─────────────────────────
        success = self.move_to_joint_angles(
            {
                'panda_joint1': 0.0,
                'panda_joint2': -0.785398,
                'panda_joint3': 0.0,
                'panda_joint4': -2.356194,
                'panda_joint5': 0.0,
                'panda_joint6': 1.570796,
                'panda_joint7': 0.785398,
            },
            'Move to home/ready position'
        )

        if success:
            self.get_logger().info('=' * 50)
            self.get_logger().info('MOTION SEQUENCE COMPLETE!')
            self.get_logger().info('Both motions executed successfully.')
            self.get_logger().info('=' * 50)


def main(args=None):
    rclpy.init(args=args)
    node = MotionTestNode()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
