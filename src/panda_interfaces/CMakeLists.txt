cmake_minimum_required(VERSION 3.8)
project(panda_interfaces)

# Find build tools
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)  # ← Generates code from .msg/.action
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

# Tell ROS2 which interface files to compile
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/DetectedObject.msg"
  "msg/SortingCommand.msg"
  "action/PickPlace.action"
  DEPENDENCIES std_msgs geometry_msgs  # ← These msgs use types from these packages
)

# Export dependencies for packages that use panda_interfaces
ament_export_dependencies(rosidl_default_runtime)

ament_package()
