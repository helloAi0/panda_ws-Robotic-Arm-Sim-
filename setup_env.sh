
# Allow Gazebo to find package:// mesh URIs
export GAZEBO_RESOURCE_PATH=$GAZEBO_RESOURCE_PATH:\
/root/panda_ws/install/panda_description/share:\
/root/panda_ws/install

export GAZEBO_MODEL_PATH=/root/panda_ws/install/panda_description/share:$GAZEBO_MODEL_PATH

export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export OGRE_RTT_MODE=Copy
