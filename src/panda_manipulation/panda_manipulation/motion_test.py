#!/usr/bin/env python3
"""
motion_test.py — Direct Joint Trajectory Controller version

Bypasses MoveGroup and sends trajectories directly to
panda_arm_controller's FollowJointTrajectory action server.
This is how ros2_control works at its core.
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory


class MotionTestNode(Node):

    JOINT_NAMES = [
        'panda_joint1', 'panda_joint2', 'panda_joint3',
        'panda_joint4', 'panda_joint5', 'panda_joint6', 'panda_joint7'
    ]

    def __init__(self):
        super().__init__('motion_test_node')
        self.get_logger().info('Motion Test Node starting...')

        self._client = ActionClient(
            self,
            FollowJointTrajectory,
            '/panda_arm_controller/follow_joint_trajectory'
        )

        self.get_logger().info('Waiting for panda_arm_controller...')
        self._client.wait_for_server()
        self.get_logger().info('Controller ready!')

        self.run_sequence()

    def send_trajectory(self, positions, duration_sec, description):
        """Send a single-point trajectory — move to target angles."""
        self.get_logger().info(f'Moving: {description}')

        traj = JointTrajectory()
        traj.joint_names = self.JOINT_NAMES

        point = JointTrajectoryPoint()
        point.positions = positions
        point.velocities = [0.0] * 7
        point.accelerations = [0.0] * 7

        # CRITICAL: time_from_start must be > 0
        # This tells the controller HOW LONG to take to reach this point
        point.time_from_start = Duration(
            sec=int(duration_sec),
            nanosec=int((duration_sec % 1) * 1e9)
        )
        traj.points = [point]

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj
        goal.goal_time_tolerance = Duration(sec=2, nanosec=0)

        future = self._client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)

        handle = future.result()
        if not handle.accepted:
            self.get_logger().error('Goal REJECTED')
            return False

        self.get_logger().info(f'Executing... (wait {duration_sec}s)')
        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        code = result_future.result().result.error_code
        if code == FollowJointTrajectory.Result.SUCCESSFUL:
            self.get_logger().info(f'SUCCESS: {description}')
            return True
        else:
            self.get_logger().error(f'FAILED code={code}: {description}')
            return False

    def run_sequence(self):
        import time

        self.get_logger().info('=' * 50)
        self.get_logger().info('STARTING MOTION SEQUENCE')
        self.get_logger().info('=' * 50)

        # Motion 1: Extended pose
        ok = self.send_trajectory(
            positions=[0.0, -0.3, 0.0, -1.5, 0.0, 1.2, 0.785],
            duration_sec=4.0,
            description='Move to extended pose'
        )
        if not ok:
            return

        time.sleep(1.0)

        # Motion 2: Home/ready pose
        ok = self.send_trajectory(
            positions=[0.0, -0.785398, 0.0, -2.356194, 0.0, 1.570796, 0.785398],
            duration_sec=4.0,
            description='Return to home pose'
        )

        if ok:
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
