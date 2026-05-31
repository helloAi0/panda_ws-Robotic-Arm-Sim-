# ============================================================
# Franka Panda Color Sorting Robot — Development Environment
# Base: ROS2 Humble on Ubuntu 22.04
# ============================================================
FROM panda_env

# Prevent interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Update package list
RUN apt-get update

# ── Core ROS2 simulation stack ──────────────────────────────
RUN apt-get install -y \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros \
  ros-humble-gazebo-plugins \
  ros-humble-xacro \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher \
  ros-humble-joint-state-publisher-gui

# ── ros2_control stack ──────────────────────────────────────
RUN apt-get install -y \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-controller-manager \
  ros-humble-joint-trajectory-controller \
  ros-humble-joint-state-broadcaster \
  ros-humble-gripper-controllers \
  ros-humble-hardware-interface \
  ros-humble-control-msgs \
  ros-humble-control-toolbox

# ── MoveIt2 ─────────────────────────────────────────────────
RUN apt-get install -y \
  ros-humble-moveit \
  ros-humble-moveit-ros-planning-interface \
  ros-humble-moveit-ros-move-group \
  ros-humble-moveit-kinematics \
  ros-humble-moveit-planners-ompl

# ── Python dependencies ──────────────────────────────────────
RUN apt-get install -y \
  python3-pip \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  git

RUN pip3 install \
  opencv-python \
  numpy \
  transforms3d

# ── Utilities ────────────────────────────────────────────────
RUN apt-get install -y \
  ros-humble-tf2-tools \
  ros-humble-tf2-ros \
  ros-humble-rqt \
  ros-humble-rqt-common-plugins \
  ros-humble-rqt-graph \
  ros-humble-rviz2

# ── Auto-source ROS2 in every bash session ───────────────────
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc
RUN echo "source /root/panda_ws/install/setup.bash 2>/dev/null || true" >> /root/.bashrc
RUN echo "export GAZEBO_PLUGIN_PATH=\$GAZEBO_PLUGIN_PATH:/root/panda_ws/install/gazebo_ros2_control/lib" >> /root/.bashrc

# Set working directory
WORKDIR /root/panda_ws


# Gazebo mesh path resolution
RUN echo "export GAZEBO_RESOURCE_PATH=\$GAZEBO_RESOURCE_PATH:/root/panda_ws/install/panda_description/share:/root/panda_ws/install" >> /root/.bashrc

# ros2 control CLI tool
RUN apt-get update && apt-get install -y ros-humble-ros2controlcli
