#!/usr/bin/env python3
"""Publishes RViz markers for cubes and bins from Gazebo model states."""
import rclpy
from rclpy.node import Node
from gazebo_msgs.msg import ModelStates
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import ColorRGBA
from geometry_msgs.msg import Vector3

COLOR_RGBA = {
    "red_cube":   ColorRGBA(r=0.9, g=0.1, b=0.1, a=0.9),
    "green_cube": ColorRGBA(r=0.1, g=0.9, b=0.1, a=0.9),
    "blue_cube":  ColorRGBA(r=0.1, g=0.1, b=0.9, a=0.9),
    "bin_red":    ColorRGBA(r=0.9, g=0.2, b=0.2, a=0.4),
    "bin_green":  ColorRGBA(r=0.2, g=0.9, b=0.2, a=0.4),
    "bin_blue":   ColorRGBA(r=0.2, g=0.2, b=0.9, a=0.4),
    "work_table": ColorRGBA(r=0.6, g=0.4, b=0.2, a=0.5),
}
CUBE_SCALE  = Vector3(x=0.04, y=0.04, z=0.04)
BIN_SCALE   = Vector3(x=0.15, y=0.15, z=0.05)
TABLE_SCALE = Vector3(x=0.8,  y=0.6,  z=0.02)


class SceneMarkerNode(Node):
    def __init__(self):
        super().__init__("scene_marker_node")
        self.create_subscription(ModelStates, "/gazebo/model_states",
                                 self._cb, 10)
        self._pub = self.create_publisher(MarkerArray, "/scene_markers", 10)
        self.get_logger().info("Scene marker publisher ready.")

    def _cb(self, msg):
        ma = MarkerArray()
        for i, name in enumerate(msg.name):
            color, scale = self._classify(name)
            if color is None:
                continue
            m = Marker()
            m.header.frame_id = "world"
            m.ns = "scene"
            m.id = i
            m.type = Marker.CUBE
            m.action = Marker.ADD
            m.pose = msg.pose[i]
            m.scale = scale
            m.color = color
            ma.markers.append(m)
        self._pub.publish(ma)

    def _classify(self, name):
        if "red_cube"   in name: return COLOR_RGBA["red_cube"],   CUBE_SCALE
        if "green_cube" in name: return COLOR_RGBA["green_cube"], CUBE_SCALE
        if "blue_cube"  in name: return COLOR_RGBA["blue_cube"],  CUBE_SCALE
        if "bin_red"    in name: return COLOR_RGBA["bin_red"],    BIN_SCALE
        if "bin_green"  in name: return COLOR_RGBA["bin_green"],  BIN_SCALE
        if "bin_blue"   in name: return COLOR_RGBA["bin_blue"],   BIN_SCALE
        if "work_table" in name: return COLOR_RGBA["work_table"], TABLE_SCALE
        return None, None


def main(args=None):
    rclpy.init(args=args)
    node = SceneMarkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
