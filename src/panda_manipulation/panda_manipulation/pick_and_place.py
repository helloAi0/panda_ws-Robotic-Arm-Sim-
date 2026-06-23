#!/usr/bin/env python3
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory
from sensor_msgs.msg import JointState
from geometry_msgs.msg import PoseStamped
from moveit_msgs.srv import GetPositionIK
from moveit_msgs.msg import RobotState as MoveItRobotState
from gazebo_msgs.msg import ModelStates
from panda_interfaces.msg import DetectedObject

ARM_JOINTS = ["panda_joint1","panda_joint2","panda_joint3","panda_joint4","panda_joint5","panda_joint6","panda_joint7"]
HAND_JOINTS = ["panda_finger_joint1","panda_finger_joint2"]
GRIPPER_OPEN   = [0.035, 0.035]
GRIPPER_CLOSED = [0.012, 0.012]
HOME_JOINTS = [0.0, -0.785398, 0.0, -2.356194, 0.0, 1.570796, 0.785398]
EE_LINK = "panda_link8"
PLANNING_GROUP = "panda_arm"
APPROACH_HEIGHT = 0.18
GRASP_Z_OFFSET  = 0.02
BIN_DROP_HEIGHT = 0.12
MOVE_DURATION   = 4.0
GRIPPER_DURATION = 1.5
BIN_NAME_MAP = {"red":"bin_red","green":"bin_green","blue":"bin_blue"}
SORT_ORDER = ["red","green","blue"]


class PickAndPlaceNode(Node):

    def __init__(self):
        super().__init__("pick_and_place_node")
        self.get_logger().info("Pick and Place Node starting...")

        self._current_joint_state = None
        self._cubes = {}
        self._bins  = {}

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST, depth=10)

        self.create_subscription(JointState, "/joint_states",
                                 self._joint_state_cb, sensor_qos)
        self.create_subscription(DetectedObject, "/detected_objects",
                                 self._detected_cb, 10)
        self.create_subscription(ModelStates, "/gazebo/model_states",
                                 self._model_states_cb, 10)

        self._ik_client  = self.create_client(GetPositionIK, "/compute_ik")
        self._arm_client = ActionClient(self, FollowJointTrajectory,
                                        "/panda_arm_controller/follow_joint_trajectory")
        self._hand_client = ActionClient(self, FollowJointTrajectory,
                                         "/panda_hand_controller/follow_joint_trajectory")

        self.get_logger().info("Waiting for /compute_ik ...")
        self._ik_client.wait_for_service()
        self.get_logger().info("Waiting for arm controller ...")
        self._arm_client.wait_for_server()
        self.get_logger().info("Waiting for hand controller ...")
        self._hand_client.wait_for_server()
        self.get_logger().info("All ready.")

        while self._current_joint_state is None:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info("Joint states received.")

        self.get_logger().info("Waiting for bin positions...")
        while len(self._bins) < 3:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info(f"Bins: {list(self._bins.keys())}")

        self.get_logger().info("Waiting for cube detections...")
        while len(self._cubes) < 3:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info(f"Cubes: {list(self._cubes.keys())}")

        self.run_sorting_sequence()

    def _joint_state_cb(self, msg):
        self._current_joint_state = msg

    def _detected_cb(self, msg):
        self._cubes[msg.color] = (msg.position.x, msg.position.y, msg.position.z)

    def _model_states_cb(self, msg):
        for i, name in enumerate(msg.name):
            for color, bin_name in BIN_NAME_MAP.items():
                if name == bin_name:
                    p = msg.pose[i].position
                    self._bins[color] = (p.x, p.y, p.z)

    def compute_ik(self, x, y, z):
        req = GetPositionIK.Request()
        req.ik_request.group_name     = PLANNING_GROUP
        req.ik_request.ik_link_name   = EE_LINK
        req.ik_request.avoid_collisions = False
        req.ik_request.timeout        = Duration(sec=2, nanosec=0)

        pose = PoseStamped()
        pose.header.frame_id  = "world"
        pose.pose.position.x  = x
        pose.pose.position.y  = y
        pose.pose.position.z  = z
        # Gripper pointing straight down
        pose.pose.orientation.x = 1.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = 0.0
        pose.pose.orientation.w = 0.0
        req.ik_request.pose_stamped = pose

        rs = MoveItRobotState()
        rs.joint_state = self._current_joint_state
        req.ik_request.robot_state = rs

        future = self._ik_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if future.result() is None:
            self.get_logger().error(f"IK timeout for ({x:.2f},{y:.2f},{z:.2f})")
            return None
        result = future.result()
        if result.error_code.val != 1:
            self.get_logger().error(
                f"IK failed code={result.error_code.val} for ({x:.2f},{y:.2f},{z:.2f})")
            return None
        name_to_pos = dict(zip(result.solution.joint_state.name,
                               result.solution.joint_state.position))
        missing = [j for j in ARM_JOINTS if j not in name_to_pos]
        if missing:
            self.get_logger().error(f"IK missing joints: {missing}")
            return None
        return [name_to_pos[j] for j in ARM_JOINTS]

    def move_arm_joints(self, joint_positions, duration=MOVE_DURATION, description=""):
        self.get_logger().info(f"Arm: {description}")
        traj = JointTrajectory()
        traj.joint_names = ARM_JOINTS
        pt = JointTrajectoryPoint()
        pt.positions  = [float(v) for v in joint_positions]
        pt.velocities = [0.0] * 7
        pt.time_from_start = Duration(sec=int(duration),
                                      nanosec=int((duration % 1) * 1e9))
        traj.points = [pt]
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj
        future = self._arm_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("Arm goal REJECTED")
            return False
        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        code = result_future.result().result.error_code
        if code != FollowJointTrajectory.Result.SUCCESSFUL:
            self.get_logger().error(f"Arm move FAILED code={code}")
            return False
        return True

    def move_to_pose(self, x, y, z, description=""):
        joints = self.compute_ik(x, y, z)
        if joints is None:
            return False
        # Update joint state belief after each move
        rclpy.spin_once(self, timeout_sec=0.1)
        return self.move_arm_joints(joints, description=description)

    def set_gripper(self, positions, description=""):
        self.get_logger().info(f"Gripper: {description}")
        traj = JointTrajectory()
        traj.joint_names = HAND_JOINTS
        pt = JointTrajectoryPoint()
        pt.positions  = [float(v) for v in positions]
        pt.velocities = [0.0, 0.0]
        pt.time_from_start = Duration(sec=int(GRIPPER_DURATION),
                                      nanosec=int((GRIPPER_DURATION % 1) * 1e9))
        traj.points = [pt]
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj
        future = self._hand_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("Gripper goal REJECTED")
            return False
        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        return True

    def pick_and_place_one(self, color):
        cx, cy, cz = self._cubes[color]
        bx, by, bz = self._bins[color]
        self.get_logger().info("=" * 50)
        self.get_logger().info(f"SORTING {color.upper()} CUBE")
        self.get_logger().info(f"  cube ({cx:.2f},{cy:.2f},{cz:.2f}) -> bin ({bx:.2f},{by:.2f},{bz:.2f})")
        self.get_logger().info("=" * 50)

        steps = [
            lambda: self.set_gripper(GRIPPER_OPEN, "open gripper"),
            lambda: self.move_to_pose(cx, cy, cz + APPROACH_HEIGHT, f"pre-grasp above {color}"),
            lambda: self.move_to_pose(cx, cy, cz + GRASP_Z_OFFSET,  f"descend to {color}"),
            lambda: self.set_gripper(GRIPPER_CLOSED, f"close on {color}"),
            lambda: self.move_to_pose(cx, cy, cz + APPROACH_HEIGHT, "lift cube"),
            lambda: self.move_to_pose(bx, by, bz + APPROACH_HEIGHT, f"pre-place above {color} bin"),
            lambda: self.move_to_pose(bx, by, bz + BIN_DROP_HEIGHT, "lower into bin"),
            lambda: self.set_gripper(GRIPPER_OPEN, "release cube"),
            lambda: self.move_to_pose(bx, by, bz + APPROACH_HEIGHT, "retreat from bin"),
        ]
        for step in steps:
            ok = step()
            if ok is False:
                self.get_logger().error(f"{color}: STEP FAILED — continuing to next cube")
                return False
            time.sleep(0.3)
        self.get_logger().info(f"{color.upper()} CUBE SORTED SUCCESSFULLY")
        return True

    def run_sorting_sequence(self):
        self.get_logger().info("#" * 50)
        self.get_logger().info("STARTING FULL SORTING SEQUENCE")
        self.get_logger().info("#" * 50)
        self.move_arm_joints(HOME_JOINTS, description="move to home")
        time.sleep(0.5)
        results = {}
        for color in SORT_ORDER:
            if color not in self._cubes or color not in self._bins:
                self.get_logger().error(f"Missing data for {color}, skipping")
                continue
            results[color] = self.pick_and_place_one(color)
            time.sleep(0.5)
        self.move_arm_joints(HOME_JOINTS, description="return home")
        self.get_logger().info("#" * 50)
        self.get_logger().info("SORTING COMPLETE")
        for c, ok in results.items():
            self.get_logger().info(f"  {c}: {'SUCCESS' if ok else 'FAILED'}")
        self.get_logger().info("#" * 50)


def main(args=None):
    rclpy.init(args=args)
    node = PickAndPlaceNode()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
