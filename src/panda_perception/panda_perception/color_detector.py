#!/usr/bin/env python3
"""
color_detector.py - Gazebo Model States version

Uses /gazebo/model_states to get exact object positions in simulation.
In a real robot, this would be replaced by camera-based HSV detection.
This is standard practice in simulation: use ground-truth positions
for testing the manipulation pipeline, validate perception separately.
"""
import rclpy
from rclpy.node import Node
from gazebo_msgs.msg import ModelStates
from panda_interfaces.msg import DetectedObject

# Map model name keywords to colors
COLOR_MAP = {
    "red":   "red",
    "green": "green",
    "blue":  "blue",
}


class ColorDetectorNode(Node):

    def __init__(self):
        super().__init__("color_detector_node")
        self.get_logger().info("Color Detector Node starting (model-states mode)...")

        self._sub = self.create_subscription(
            ModelStates,
            "/gazebo/model_states",
            self._model_states_callback,
            10
        )

        self._pub = self.create_publisher(DetectedObject, "/detected_objects", 10)

        self._detected = {}   # color -> DetectedObject (deduplicated)
        self._log_timer = self.create_timer(3.0, self._log_detections)

        self.get_logger().info("Subscribed to /gazebo/model_states. Waiting...")

    def _model_states_callback(self, msg: ModelStates):
        self._detected.clear()

        for i, name in enumerate(msg.name):
            color = self._get_color(name)
            if color is None:
                continue

            pose = msg.pose[i]

            det = DetectedObject()
            det.header.stamp = self.get_clock().now().to_msg()
            det.header.frame_id = "world"
            det.color = color
            det.position.x = pose.position.x
            det.position.y = pose.position.y
            det.position.z = pose.position.z
            det.confidence = 1.0   # ground-truth in simulation
            det.object_id = name
            det.radius = 0.02

            self._detected[color] = det
            self._pub.publish(det)

    def _get_color(self, name: str) -> str:
        name_lower = name.lower()
        for keyword, color in COLOR_MAP.items():
            if keyword in name_lower:
                return color
        return None

    def _log_detections(self):
        if self._detected:
            summary = ", ".join(
                f"{c}@({d.position.x:.2f},{d.position.y:.2f},{d.position.z:.2f})"
                for c, d in self._detected.items()
            )
            self.get_logger().info(f"Detected: {summary}")
        else:
            self.get_logger().info("No colored objects detected yet...")


def main(args=None):
    rclpy.init(args=args)
    node = ColorDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
