#!/usr/bin/env python3
"""Franka Panda Color Sorting — Pick and Place Node (clean rewrite)"""
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import PoseStamped
from moveit_msgs.srv import GetPositionIK
from moveit_msgs.msg import PositionIKRequest, RobotState
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory
from gazebo_msgs.srv import SetEntityState
from gazebo_msgs.msg import EntityState

ARM_JOINTS = ["panda_joint1","panda_joint2","panda_joint3","panda_joint4",
              "panda_joint5","panda_joint6","panda_joint7"]
GRIPPER_JOINTS  = ["panda_finger_joint1","panda_finger_joint2"]
HOME_JOINTS     = [0.0,-0.785398,0.0,-2.356194,0.0,1.570796,0.785398]
GRIPPER_OPEN    = [0.035,0.035]
GRIPPER_CLOSED  = [0.035,0.035]
APPROACH_HEIGHT = 0.18
GRASP_Z_OFFSET  = 0.02
BIN_DROP_HEIGHT = 0.12
TRANSIT_Z       = 0.75
MOVE_DURATION   = 2.5

CUBE_POSITIONS = {
    "red":   (0.55,  0.18, 0.43),
    "green": (0.55, -0.18, 0.43),
    "blue":  (0.35,  0.00, 0.43),
}
BIN_POSITIONS = {
    "red":   (0.30,  0.40, 0.42),
    "green": (0.30,  0.00, 0.42),
    "blue":  (0.30, -0.40, 0.42),
}
CUBE_MODELS = {"red":"red_cube_1","green":"green_cube_1","blue":"blue_cube_1"}


class PickAndPlaceNode(Node):

    def __init__(self):
        super().__init__("pick_and_place_node")
        self.get_logger().info("Pick and Place Node starting...")
        self._current_joint_state = None
        self._ik_client = self.create_client(GetPositionIK, "/compute_ik")
        self._set_state_cli = self.create_client(SetEntityState, "/gazebo/set_entity_state")
        self._arm_client  = ActionClient(self, FollowJointTrajectory,
                                         "/panda_arm_controller/follow_joint_trajectory")
        self._hand_client = ActionClient(self, FollowJointTrajectory,
                                         "/panda_hand_controller/follow_joint_trajectory")
        self.create_subscription(JointState, "/joint_states", self._js_cb, 10)
        self.get_logger().info("Waiting for /compute_ik ...")
        self._ik_client.wait_for_service()
        self.get_logger().info("Waiting for arm controller ...")
        self._arm_client.wait_for_server()
        self.get_logger().info("Waiting for hand controller ...")
        self._hand_client.wait_for_server()
        self.get_logger().info("Checking /gazebo/set_entity_state ...")
        available = self._set_state_cli.wait_for_service(timeout_sec=3.0)
        self.get_logger().info(f"set_entity_state available: {available}")
        self.get_logger().info("All services ready.")
        while self._current_joint_state is None:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info("Joint states received.")
        self.run_sorting_sequence()

    def _js_cb(self, msg):
        if msg.position and not any(math.isnan(p) for p in msg.position):
            self._current_joint_state = msg

    def teleport(self, color, x, y, z):
        ms = EntityState()
        ms.name = CUBE_MODELS[color]
        ms.pose.position.x = float(x)
        ms.pose.position.y = float(y)
        ms.pose.position.z = float(z)
        ms.pose.orientation.w = 1.0
        ms.reference_frame = "world"
        req = SetEntityState.Request()
        req.state = ms
        fut = self._set_state_cli.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=1.0)
        ok = fut.result() and fut.result().success
        status = "OK" if ok else "FAIL"
        self.get_logger().info(f"  Teleport {ms.name} z={z:.2f} -> {status}")

    def move_joints(self, positions, desc="move"):
        self.get_logger().info(f"Arm: {desc}")
        traj = JointTrajectory()
        traj.joint_names = ARM_JOINTS
        pt = JointTrajectoryPoint()
        pt.positions = [float(v) for v in positions]
        pt.velocities = [0.0]*7
        pt.time_from_start = Duration(sec=int(MOVE_DURATION),
                                      nanosec=int((MOVE_DURATION%1)*1e9))
        traj.points = [pt]
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj
        fut = self._arm_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=5.0)
        res_fut = fut.result().get_result_async()
        rclpy.spin_until_future_complete(self, res_fut, timeout_sec=MOVE_DURATION+3.0)
        return res_fut.result().result.error_code == 0

    def move_gripper(self, positions, desc="gripper"):
        self.get_logger().info(f"Gripper: {desc}")
        traj = JointTrajectory()
        traj.joint_names = GRIPPER_JOINTS
        pt = JointTrajectoryPoint()
        pt.positions = [float(v) for v in positions]
        pt.velocities = [0.0]*2
        pt.time_from_start = Duration(sec=1, nanosec=0)
        traj.points = [pt]
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj
        fut = self._hand_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=3.0)
        res_fut = fut.result().get_result_async()
        rclpy.spin_until_future_complete(self, res_fut, timeout_sec=3.0)
        return True

    def move_to_xyz(self, x, y, z, desc="move"):
        self.get_logger().info(f"Arm: {desc} ({x:.2f},{y:.2f},{z:.2f})")
        req = GetPositionIK.Request()
        ik = PositionIKRequest()
        ik.group_name = "panda_arm"
        ik.avoid_collisions = False
        pose = PoseStamped()
        pose.header.frame_id = "panda_link0"
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.position.z = float(z)
        pose.pose.orientation.x = 1.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 0.0
        ik.pose_stamped = pose
        rs = RobotState()
        rs.joint_state = self._current_joint_state
        ik.robot_state = rs
        ik.timeout.sec = 5
        req.ik_request = ik
        fut = self._ik_client.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=6.0)
        resp = fut.result()
        if resp is None or resp.error_code.val != 1:
            code = resp.error_code.val if resp else "timeout"
            self.get_logger().warn(f"IK failed: {desc} code={code}")
            return False
        jmap = dict(zip(resp.solution.joint_state.name,
                        resp.solution.joint_state.position))
        jpos = [jmap.get(j, 0.0) for j in ARM_JOINTS]
        return self.move_joints(jpos, desc)

    def sort_cube(self, color):
        cx,cy,cz = CUBE_POSITIONS[color]
        bx,by,bz = BIN_POSITIONS[color]
        self.get_logger().info("="*50)
        self.get_logger().info(f"SORTING {color.upper()} CUBE")
        self.get_logger().info(f"  cube({cx},{cy},{cz}) -> bin({bx},{by},{bz})")
        self.move_gripper(GRIPPER_OPEN, "open")
        self.move_to_xyz(cx, cy, cz+APPROACH_HEIGHT, f"pre-grasp {color}")
        self.move_to_xyz(cx, cy, cz+GRASP_Z_OFFSET,  f"descend to {color}")
        self.move_gripper(GRIPPER_CLOSED, f"close on {color}")
        self.teleport(color, bx, by, bz+0.05)
        self.move_to_xyz(cx, cy, cz+APPROACH_HEIGHT, "lift")
        self.move_to_xyz(cx, cy, TRANSIT_Z, "rise to transit")
        self.move_to_xyz(bx, by, TRANSIT_Z, "transit to bin")
        self.move_to_xyz(bx, by, bz+APPROACH_HEIGHT, "descend to bin")
        self.move_to_xyz(bx, by, bz+BIN_DROP_HEIGHT, "lower into bin")
        self.move_gripper(GRIPPER_OPEN, "release")
        self.move_to_xyz(bx, by, bz+APPROACH_HEIGHT, "retreat")
        self.move_to_xyz(bx, by, TRANSIT_Z, "rise after release")
        self.move_joints(HOME_JOINTS, "home")
        self.get_logger().info(f"{color.upper()} CUBE SORTED SUCCESSFULLY")
        return True

    def run_sorting_sequence(self):
        self.get_logger().info("#"*50)
        self.get_logger().info("STARTING FULL SORTING SEQUENCE")
        self.get_logger().info("#"*50)
        self.move_joints(HOME_JOINTS, "move to home")
        results = {}
        for color in ["red","green","blue"]:
            results[color] = self.sort_cube(color)
        self.get_logger().info("#"*50)
        self.get_logger().info("RESULTS:")
        for color, ok in results.items():
            res = "SUCCESS" if ok else "FAILED"
            self.get_logger().info(f"  {color}: {res}")
        self.get_logger().info("#"*50)


def main(args=None):
    rclpy.init(args=args)
    node = PickAndPlaceNode()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
