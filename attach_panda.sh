#!/bin/bash
# Attaches to the running panda_ws container
docker exec -it panda_ws bash -c \
  "source /opt/ros/humble/setup.bash && \
   source /root/panda_ws/install/setup.bash 2>/dev/null && \
   export GAZEBO_MODEL_DATABASE_URI='' && \
   export GAZEBO_PLUGIN_PATH=/root/panda_ws/install/gazebo_ros2_control/lib:/opt/ros/humble/lib && \
   bash"
