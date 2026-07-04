#!/bin/bash
xhost +local:docker
docker run -it --rm \
  --name panda_ws \
  --net=host \
  --env="DISPLAY=$DISPLAY" \
  --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
  --volume="$HOME/panda_ws:/root/panda_ws" \
  panda_env:latest \
  bash
