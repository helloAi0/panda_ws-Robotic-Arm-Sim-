# SortingCommand.msg
# Command sent from orchestrator to manipulation system
# Tells the robot: pick THIS object, place it THERE

std_msgs/Header header
string object_id                    # Which object to pick
string color                        # Object color
geometry_msgs/Pose pick_pose        # Where to pick from (full pose: position + orientation)
geometry_msgs/Pose place_pose       # Where to place it
string status                       # "pending", "in_progress", "done", "failed"
