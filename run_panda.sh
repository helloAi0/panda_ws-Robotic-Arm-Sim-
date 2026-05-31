#!/bin/bash
# Run the Panda ROS2 development container
xhost +local:docker
docker run -it --rm \
  --net=host \
  --env="DISPLAY=$DISPLAY" \
  --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
  --volume="$(pwd):/root/panda_ws" \
  panda_env \
  bash
