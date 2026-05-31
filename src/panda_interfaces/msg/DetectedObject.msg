# DetectedObject.msg
# Represents a single object detected by the camera
# Used by: panda_perception → panda_sorting

std_msgs/Header header          # Timestamp + frame_id (which camera frame)
string color                    # "red", "green", "blue", "yellow"
geometry_msgs/Point position    # 3D position in camera frame (meters)
geometry_msgs/Point world_position  # 3D position in world frame (after TF)
float32 confidence              # Detection confidence 0.0 to 1.0
string object_id                # Unique ID e.g. "red_cube_001"
float32 radius                  # Approximate object radius (meters)
