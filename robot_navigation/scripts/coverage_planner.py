#!/usr/bin/env python3

# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient
# from rclpy.qos import QoSProfile, DurabilityPolicy
# from geometry_msgs.msg import PointStamped, PoseStamped, Quaternion, Point
# from nav_msgs.msg import Path
# from nav2_msgs.action import NavigateThroughPoses
# from visualization_msgs.msg import Marker
# import math

# # NEW: Import TF2 modules to get the robot's current position
# from tf2_ros import TransformException
# from tf2_ros.buffer import Buffer
# from tf2_ros.transform_listener import TransformListener

# class CoveragePlanner(Node):
#     def __init__(self):
#         super().__init__('coverage_planner')
        
#         # Subscribers and Publishers
#         self.subscription = self.create_subscription(PointStamped, '/clicked_point', self.point_callback, 10)
#         self.path_publisher = self.create_publisher(Path, '/coverage_path', 10)
        
#         marker_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
#         self.boundary_publisher = self.create_publisher(Marker, '/coverage_boundary', marker_qos)
        
#         # Action Client for Nav2
#         self.nav_client = ActionClient(self, NavigateThroughPoses, 'navigate_through_poses')
        
#         # NEW: Initialize the TF2 buffer and listener
#         self.tf_buffer = Buffer()
#         self.tf_listener = TransformListener(self.tf_buffer, self)
        
#         self.clicked_points = []
        
#         # UPDATE: Vacuum tool width set to 300mm (0.3m)
#         self.sweep_spacing = 0.30 

#         self.get_logger().info("Coverage Planner ready. Click 4 points in RViz.")

#     def point_callback(self, msg):
#         self.clicked_points.append(msg.point)
#         self.get_logger().info(f"Point {len(self.clicked_points)} received.")

#         if len(self.clicked_points) == 4:
#             self.get_logger().info("Calculating path and boundary...")
#             self.generate_and_execute_path()
#             self.clicked_points.clear() 

#     def generate_and_execute_path(self):
#         x_coords = [p.x for p in self.clicked_points]
#         y_coords = [p.y for p in self.clicked_points]
#         min_x, max_x = min(x_coords), max(x_coords)
#         min_y, max_y = min(y_coords), max(y_coords)

#         # Publish the green boundary marker
#         self.publish_boundary(min_x, max_x, min_y, max_y)

#         # 1. Get the robot's current position to find the nearest corner
#         robot_x = min_x # Fallbacks in case TF fails
#         robot_y = min_y
        
#         try:
#             # Look up the transform from base_link to map
#             t = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
#             robot_x = t.transform.translation.x
#             robot_y = t.transform.translation.y
#             self.get_logger().info(f"Robot found at X: {robot_x:.2f}, Y: {robot_y:.2f}")
#         except TransformException as ex:
#             self.get_logger().warn(f"Could not get robot pose, defaulting to bottom-left corner. Error: {ex}")

#         # 2. Define the 4 corners
#         corners = {
#             'bottom_left': (min_x, min_y),
#             'top_left': (min_x, max_y),
#             'bottom_right': (max_x, min_y),
#             'top_right': (max_x, max_y)
#         }

#         # 3. Calculate distances and find the closest corner
#         closest_corner = min(corners, key=lambda k: math.hypot(robot_x - corners[k][0], robot_y - corners[k][1]))
#         self.get_logger().info(f"Nearest corner is: {closest_corner}")

#         # 4. Generate Boustrophedon path starting from the closest corner
#         waypoints = []
        
#         # Determine starting X and direction of sweep across the X-axis
#         if closest_corner in ['bottom_left', 'top_left']:
#             current_x = min_x
#             step_x = self.sweep_spacing
#             end_condition = lambda x: x <= max_x
#         else:
#             current_x = max_x
#             step_x = -self.sweep_spacing
#             end_condition = lambda x: x >= min_x

#         # Determine initial Y direction
#         going_up = (closest_corner in ['bottom_left', 'bottom_right'])

#         while end_condition(current_x):
#             if going_up:
#                 waypoints.append((current_x, min_y))
#                 waypoints.append((current_x, max_y))
#             else:
#                 waypoints.append((current_x, max_y))
#                 waypoints.append((current_x, min_y))
            
#             going_up = not going_up
#             current_x += step_x

#         # Create Pose messages
#         poses = []
#         path_msg = Path()
#         path_msg.header.frame_id = 'map'
#         path_msg.header.stamp = self.get_clock().now().to_msg()

#         for i in range(len(waypoints)):
#             x, y = waypoints[i]
#             pose = PoseStamped()
#             pose.header = path_msg.header
#             pose.pose.position.x = float(x)
#             pose.pose.position.y = float(y)
#             pose.pose.position.z = 0.0
            
#             if i < len(waypoints) - 1:
#                 next_x, next_y = waypoints[i+1]
#                 yaw = math.atan2(next_y - y, next_x - x)
#             else:
#                 yaw = 0.0 

#             pose.pose.orientation = self.yaw_to_quaternion(yaw)
#             poses.append(pose)
#             path_msg.poses.append(pose)

#         # Publish Path and Send to Nav2
#         self.path_publisher.publish(path_msg)
#         self.send_nav2_goal(poses)

#     def publish_boundary(self, min_x, max_x, min_y, max_y):
#         marker = Marker()
#         marker.header.frame_id = 'map'
#         marker.header.stamp.sec = 0
#         marker.header.stamp.nanosec = 0
#         marker.ns = 'cleaning_zone'
#         marker.id = 0
#         marker.type = Marker.LINE_STRIP
#         marker.action = Marker.ADD
        
#         marker.pose.orientation.w = 1.0 
        
#         marker.scale.x = 0.05 
#         marker.scale.y = 0.05
#         marker.scale.z = 0.05
        
#         marker.color.r = 0.0
#         marker.color.g = 1.0
#         marker.color.b = 0.0
#         marker.color.a = 1.0 
        
#         corners = [
#             (min_x, min_y),
#             (max_x, min_y),
#             (max_x, max_y),
#             (min_x, max_y),
#             (min_x, min_y) 
#         ]
        
#         for x, y in corners:
#             p = Point()
#             p.x = float(x)
#             p.y = float(y)
#             p.z = 0.05
#             marker.points.append(p)
            
#         self.boundary_publisher.publish(marker)

#     def yaw_to_quaternion(self, yaw):
#         q = Quaternion()
#         q.x = 0.0
#         q.y = 0.0
#         q.z = math.sin(yaw / 2.0)
#         q.w = math.cos(yaw / 2.0)
#         return q

#     def send_nav2_goal(self, poses):
#         self.get_logger().info("Waiting for Nav2 server...")
#         self.nav_client.wait_for_server()
        
#         goal_msg = NavigateThroughPoses.Goal()
#         goal_msg.poses = poses
        
#         self.get_logger().info(f"Sending {len(poses)} waypoints to Nav2.")
#         self.nav_client.send_goal_async(goal_msg)

# def main(args=None):
#     rclpy.init(args=args)
#     node = CoveragePlanner()
#     rclpy.spin(node)
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == '__main__':
#     main()
# --------------------------------------------------------------------------------

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, DurabilityPolicy
from geometry_msgs.msg import PointStamped, PoseStamped, Quaternion, Point
from nav_msgs.msg import Path
from nav2_msgs.action import NavigateThroughPoses
from visualization_msgs.msg import Marker
import math

# NEW: Import TF2 modules to get the robot's current position
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

class CoveragePlanner(Node):
    def __init__(self):
        super().__init__('coverage_planner')
        
        # Subscribers and Publishers
        self.subscription = self.create_subscription(PointStamped, '/clicked_point', self.point_callback, 10)
        self.path_publisher = self.create_publisher(Path, '/coverage_path', 10)
        
        marker_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.boundary_publisher = self.create_publisher(Marker, '/coverage_boundary', marker_qos)
        
        # Action Client for Nav2
        self.nav_client = ActionClient(self, NavigateThroughPoses, 'navigate_through_poses')
        
        # NEW: Initialize the TF2 buffer and listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        self.clicked_points = []
        
        # UPDATE: Vacuum tool width set to 300mm (0.3m)
        self.sweep_spacing = 0.30 

        self.get_logger().info("Coverage Planner ready. Click 4 points in RViz.")

    def point_callback(self, msg):
        self.clicked_points.append(msg.point)
        self.get_logger().info(f"Point {len(self.clicked_points)} received.")

        if len(self.clicked_points) == 4:
            self.get_logger().info("Calculating path and boundary...")
            self.generate_and_execute_path()
            self.clicked_points.clear() 

    def generate_and_execute_path(self):
        x_coords = [p.x for p in self.clicked_points]
        y_coords = [p.y for p in self.clicked_points]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        # Publish the green boundary marker
        self.publish_boundary(min_x, max_x, min_y, max_y)

        # 1. Get the robot's current position to find the nearest corner
        robot_x = min_x # Fallbacks in case TF fails
        robot_y = min_y
        
        try:
            # Look up the transform from base_link to map
            t = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
            robot_x = t.transform.translation.x
            robot_y = t.transform.translation.y
            self.get_logger().info(f"Robot found at X: {robot_x:.2f}, Y: {robot_y:.2f}")
        except TransformException as ex:
            self.get_logger().warn(f"Could not get robot pose, defaulting to bottom-left corner. Error: {ex}")

        # 2. Define the 4 corners
        corners = {
            'bottom_left': (min_x, min_y),
            'top_left': (min_x, max_y),
            'bottom_right': (max_x, min_y),
            'top_right': (max_x, max_y)
        }

        # 3. Calculate distances and find the closest corner
        closest_corner = min(corners, key=lambda k: math.hypot(robot_x - corners[k][0], robot_y - corners[k][1]))
        self.get_logger().info(f"Nearest corner is: {closest_corner}")

        # 4. Generate Boustrophedon path starting from the closest corner
        waypoints = []
        
        # Determine starting X and direction of sweep across the X-axis
        if closest_corner in ['bottom_left', 'top_left']:
            current_x = min_x
            step_x = self.sweep_spacing
            end_condition = lambda x: x <= max_x
        else:
            current_x = max_x
            step_x = -self.sweep_spacing
            end_condition = lambda x: x >= min_x

        # Determine initial Y direction
        going_up = (closest_corner in ['bottom_left', 'bottom_right'])

        while end_condition(current_x):
            if going_up:
                waypoints.append((current_x, min_y))
                waypoints.append((current_x, max_y))
            else:
                waypoints.append((current_x, max_y))
                waypoints.append((current_x, min_y))
            
            going_up = not going_up
            current_x += step_x

        # Create Pose messages
        poses = []
        path_msg = Path()
        path_msg.header.frame_id = 'map'
        path_msg.header.stamp = self.get_clock().now().to_msg()

        for i in range(len(waypoints)):
            x, y = waypoints[i]
            pose = PoseStamped()
            pose.header = path_msg.header
            pose.pose.position.x = float(x)
            pose.pose.position.y = float(y)
            pose.pose.position.z = 0.0
            
            if i < len(waypoints) - 1:
                next_x, next_y = waypoints[i+1]
                yaw = math.atan2(next_y - y, next_x - x)
            else:
                yaw = 0.0 

            pose.pose.orientation = self.yaw_to_quaternion(yaw)
            poses.append(pose)
            path_msg.poses.append(pose)

        # Publish Path and Send to Nav2
        self.path_publisher.publish(path_msg)
        self.send_nav2_goal(poses)

    def publish_boundary(self, min_x, max_x, min_y, max_y):
        marker = Marker()
        marker.header.frame_id = 'map'
        marker.header.stamp.sec = 0
        marker.header.stamp.nanosec = 0
        marker.ns = 'cleaning_zone'
        marker.id = 0
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        
        marker.pose.orientation.w = 1.0 
        
        marker.scale.x = 0.05 
        marker.scale.y = 0.05
        marker.scale.z = 0.05
        
        marker.color.r = 0.0
        marker.color.g = 1.0
        marker.color.b = 0.0
        marker.color.a = 1.0 
        
        corners = [
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
            (min_x, min_y) 
        ]
        
        for x, y in corners:
            p = Point()
            p.x = float(x)
            p.y = float(y)
            p.z = 0.05
            marker.points.append(p)
            
        self.boundary_publisher.publish(marker)

    def yaw_to_quaternion(self, yaw):
        q = Quaternion()
        q.x = 0.0
        q.y = 0.0
        q.z = math.sin(yaw / 2.0)
        q.w = math.cos(yaw / 2.0)
        return q

    def send_nav2_goal(self, poses):
        self.get_logger().info("Waiting for Nav2 server...")
        self.nav_client.wait_for_server()
        
        goal_msg = NavigateThroughPoses.Goal()
        goal_msg.poses = poses
        
        self.get_logger().info(f"Sending {len(poses)} waypoints to Nav2.")
        
        # MODIFIED: Send goal and track completion
        self.send_goal_future = self.nav_client.send_goal_async(goal_msg)
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    # --- ADDED: Handle feedback and inject home pose when finished ---
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected by Nav2 server.')
            return
        self.get_logger().info('Coverage path accepted. Executing...')
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        self.get_logger().info('Coverage task finished! Injecting initial pose to return to dock.')
        
        dock_pose = PoseStamped()
        dock_pose.header.frame_id = 'map'
        dock_pose.header.stamp = self.get_clock().now().to_msg()
        dock_pose.pose.position.x = 3.355494   #
        dock_pose.pose.position.y = -0.881754  #
        dock_pose.pose.position.z = 0.0        #
        dock_pose.pose.orientation = self.yaw_to_quaternion(-0.020110) #

        goal_msg = NavigateThroughPoses.Goal()
        goal_msg.poses = [dock_pose]
        self.nav_client.send_goal_async(goal_msg)
    # -----------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = CoveragePlanner()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()




# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient
# from rclpy.qos import QoSProfile, DurabilityPolicy
# from geometry_msgs.msg import PointStamped, PoseStamped, Quaternion, Point
# from nav_msgs.msg import Path
# from nav2_msgs.action import NavigateThroughPoses
# from visualization_msgs.msg import Marker
# import math

# # NEW: Import TF2 modules to get the robot's current position
# from tf2_ros import TransformException
# from tf2_ros.buffer import Buffer
# from tf2_ros.transform_listener import TransformListener

# class CoveragePlanner(Node):
#     def __init__(self):
#         super().__init__('coverage_planner')
        
#         # Subscribers and Publishers
#         self.subscription = self.create_subscription(PointStamped, '/clicked_point', self.point_callback, 10)
#         self.path_publisher = self.create_publisher(Path, '/coverage_path', 10)
        
#         marker_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
#         self.boundary_publisher = self.create_publisher(Marker, '/coverage_boundary', marker_qos)
        
#         # Action Client for Nav2
#         self.nav_client = ActionClient(self, NavigateThroughPoses, 'navigate_through_poses')
        
#         # NEW: Initialize the TF2 buffer and listener
#         self.tf_buffer = Buffer()
#         self.tf_listener = TransformListener(self.tf_buffer, self)
        
#         self.clicked_points = []
        
#         # UPDATE: Vacuum tool width set to 300mm (0.3m)
#         self.sweep_spacing = 0.30 

#         self.get_logger().info("Coverage Planner ready. Click 4 points in RViz.")

#     def point_callback(self, msg):
#         self.clicked_points.append(msg.point)
#         self.get_logger().info(f"Point {len(self.clicked_points)} received.")

#         if len(self.clicked_points) == 4:
#             self.get_logger().info("Calculating path and boundary...")
#             self.generate_and_execute_path()
#             self.clicked_points.clear() 

#     def generate_and_execute_path(self):
#         x_coords = [p.x for p in self.clicked_points]
#         y_coords = [p.y for p in self.clicked_points]
#         min_x, max_x = min(x_coords), max(x_coords)
#         min_y, max_y = min(y_coords), max(y_coords)

#         # Publish the green boundary marker
#         self.publish_boundary(min_x, max_x, min_y, max_y)

#         # 1. Get the robot's current position to find the nearest corner
#         robot_x = min_x # Fallbacks in case TF fails
#         robot_y = min_y
        
#         try:
#             # Look up the transform from base_link to map
#             t = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
#             robot_x = t.transform.translation.x
#             robot_y = t.transform.translation.y
#             self.get_logger().info(f"Robot found at X: {robot_x:.2f}, Y: {robot_y:.2f}")
#         except TransformException as ex:
#             self.get_logger().warn(f"Could not get robot pose, defaulting to bottom-left corner. Error: {ex}")

#         # 2. Define the 4 corners
#         corners = {
#             'bottom_left': (min_x, min_y),
#             'top_left': (min_x, max_y),
#             'bottom_right': (max_x, min_y),
#             'top_right': (max_x, max_y)
#         }

#         # 3. Calculate distances and find the closest corner
#         closest_corner = min(corners, key=lambda k: math.hypot(robot_x - corners[k][0], robot_y - corners[k][1]))
#         self.get_logger().info(f"Nearest corner is: {closest_corner}")

#         # 4. Generate Boustrophedon path starting from the closest corner
#         waypoints = []
        
#         # Determine starting X and direction of sweep across the X-axis
#         if closest_corner in ['bottom_left', 'top_left']:
#             current_x = min_x
#             step_x = self.sweep_spacing
#             end_condition = lambda x: x <= max_x
#         else:
#             current_x = max_x
#             step_x = -self.sweep_spacing
#             end_condition = lambda x: x >= min_x

#         # Determine initial Y direction
#         going_up = (closest_corner in ['bottom_left', 'bottom_right'])

#         while end_condition(current_x):
#             if going_up:
#                 waypoints.append((current_x, min_y))
#                 waypoints.append((current_x, max_y))
#             else:
#                 waypoints.append((current_x, max_y))
#                 waypoints.append((current_x, min_y))
            
#             going_up = not going_up
#             current_x += step_x

#         # Create Pose messages
#         poses = []
#         path_msg = Path()
#         path_msg.header.frame_id = 'map'
#         path_msg.header.stamp = self.get_clock().now().to_msg()

#         for i in range(len(waypoints)):
#             x, y = waypoints[i]
#             pose = PoseStamped()
#             pose.header = path_msg.header
#             pose.pose.position.x = float(x)
#             pose.pose.position.y = float(y)
#             pose.pose.position.z = 0.0
            
#             if i < len(waypoints) - 1:
#                 next_x, next_y = waypoints[i+1]
#                 yaw = math.atan2(next_y - y, next_x - x)
#             else:
#                 yaw = 0.0 

#             pose.pose.orientation = self.yaw_to_quaternion(yaw)
#             poses.append(pose)
#             path_msg.poses.append(pose)

#         # --- INJECT INITIAL POSE AS LAST WAYPOINT TO RETURN DOCK ---
#         dock_pose = PoseStamped()
#         dock_pose.header = path_msg.header
#         dock_pose.pose.position.x = 3.355494
#         dock_pose.pose.position.y = -0.881754
#         dock_pose.pose.position.z = 0.0
#         dock_pose.pose.orientation = self.yaw_to_quaternion(-0.020110)
        
#         poses.append(dock_pose)
#         path_msg.poses.append(dock_pose)
#         # -----------------------------------------------------------

#         # Publish Path and Send to Nav2
#         self.path_publisher.publish(path_msg)
#         self.send_nav2_goal(poses)

#     def publish_boundary(self, min_x, max_x, min_y, max_y):
#         marker = Marker()
#         marker.header.frame_id = 'map'
#         marker.header.stamp.sec = 0
#         marker.header.stamp.nanosec = 0
#         marker.ns = 'cleaning_zone'
#         marker.id = 0
#         marker.type = Marker.LINE_STRIP
#         marker.action = Marker.ADD
        
#         marker.pose.orientation.w = 1.0 
        
#         marker.scale.x = 0.05 
#         marker.scale.y = 0.05
#         marker.scale.z = 0.05
        
#         marker.color.r = 0.0
#         marker.color.g = 1.0
#         marker.color.b = 0.0
#         marker.color.a = 1.0 
        
#         corners = [
#             (min_x, min_y),
#             (max_x, min_y),
#             (max_x, max_y),
#             (min_x, max_y),
#             (min_x, min_y) 
#         ]
        
#         for x, y in corners:
#             p = Point()
#             p.x = float(x)
#             p.y = float(y)
#             p.z = 0.05
#             marker.points.append(p)
            
#         self.boundary_publisher.publish(marker)

#     def yaw_to_quaternion(self, yaw):
#         q = Quaternion()
#         q.x = 0.0
#         q.y = 0.0
#         q.z = math.sin(yaw / 2.0)
#         q.w = math.cos(yaw / 2.0)
#         return q

#     def send_nav2_goal(self, poses):
#         self.get_logger().info("Waiting for Nav2 server...")
#         self.nav_client.wait_for_server()
        
#         goal_msg = NavigateThroughPoses.Goal()
#         goal_msg.poses = poses
        
#         self.get_logger().info(f"Sending {len(poses)} waypoints to Nav2.")
#         self.nav_client.send_goal_async(goal_msg)

# def main(args=None):
#     rclpy.init(args=args)
#     node = CoveragePlanner()
#     rclpy.spin(node)
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == '__main__':
#     main()
# -------------------------------------------------------------------------------

# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient
# from rclpy.qos import QoSProfile, DurabilityPolicy
# from geometry_msgs.msg import PointStamped, PoseStamped, Quaternion, Point
# from nav_msgs.msg import Path
# from nav2_msgs.action import NavigateToPose, Spin
# from visualization_msgs.msg import Marker
# import math
# import threading

# class CoveragePlanner(Node):
#     def __init__(self):
#         super().__init__('coverage_planner')
        
#         # --- HOME POSE (From amcl_config.yaml) ---
#         self.home_x = 3.313182 #
#         self.home_y = -0.905998 #
#         self.home_yaw = -0.020110 #
#         # ---------------------------------------
        
#         # ROS Communications
#         self.subscription = self.create_subscription(PointStamped, '/clicked_point', self.point_callback, 10)
#         self.path_publisher = self.create_publisher(Path, '/coverage_path', 10)
        
#         marker_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
#         self.boundary_publisher = self.create_publisher(Marker, '/coverage_boundary', marker_qos)
        
#         # Action Clients
#         self.nav_to_pose_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
#         self.spin_client = ActionClient(self, Spin, 'spin')
        
#         self.clicked_points = []
#         self.sweep_spacing = 0.30 
#         self.get_logger().info("Coverage Planner Ready. Select 4 points in RViz.")

#     def point_callback(self, msg):
#         self.clicked_points.append(msg.point)
#         self.get_logger().info(f"Received point {len(self.clicked_points)}/4")
        
#         if len(self.clicked_points) == 4:
#             self.get_logger().info("Generating Mission Path...")
#             self.generate_and_execute_path()
#             self.clicked_points.clear() 

#     def generate_and_execute_path(self):
#         # Determine Area Boundary
#         x_coords = [p.x for p in self.clicked_points]
#         y_coords = [p.y for p in self.clicked_points]
#         min_x, max_x = min(x_coords), max(x_coords)
#         min_y, max_y = min(y_coords), max(y_coords)

#         # 1. Generate Boustrophedon Waypoints
#         waypoints = self.calculate_waypoints(min_x, max_x, min_y, max_y)
        
#         # 2. Convert to list of PoseStamped for the mission
#         mission_poses = []
#         path_msg = Path()
#         path_msg.header.frame_id = 'map'
#         path_msg.header.stamp = self.get_clock().now().to_msg()

#         # Add coverage waypoints
#         for i, (x, y) in enumerate(waypoints):
#             p = PoseStamped()
#             p.header = path_msg.header
#             p.pose.position.x = float(x)
#             p.pose.position.y = float(y)
            
#             # Lookahead for orientation
#             if i < len(waypoints) - 1:
#                 next_pt = waypoints[i+1]
#             else:
#                 next_pt = (self.home_x, self.home_y) # Face home after last coverage point
            
#             yaw = math.atan2(next_pt[1] - y, next_pt[0] - x)
#             p.pose.orientation = self.yaw_to_quaternion(yaw)
#             mission_poses.append(p)
#             path_msg.poses.append(p)

#         # 3. Add Home Pose as final destination
#         home_pose = PoseStamped()
#         home_pose.header = path_msg.header
#         home_pose.pose.position.x = self.home_x
#         home_pose.pose.position.y = self.home_y
#         home_pose.pose.orientation = self.yaw_to_quaternion(self.home_yaw)
#         mission_poses.append(home_pose)
#         path_msg.poses.append(home_pose)

#         # Publish visual path to RViz
#         self.path_publisher.publish(path_msg)
#         self.publish_boundary(min_x, max_x, min_y, max_y)

#         # 4. Start Sequential Mission Thread
#         threading.Thread(target=self.run_mission, args=(mission_poses,)).start()

#     def run_mission(self, poses):
#         total = len(poses)
#         for i, pose in enumerate(poses):
#             self.get_logger().info(f"Moving to Waypoint {i+1}/{total}...")
            
#             # Step A: Move to Pose
#             nav_goal = NavigateToPose.Goal()
#             nav_goal.pose = pose
#             self.send_action_sync(self.nav_to_pose_client, nav_goal)
            
#             # Step B: Stop and Spin (Skip spin if it's the home pose)
#             if i < total - 1:
#                 self.get_logger().info("Arrived. Performing 360 spin...")
#                 spin_goal = Spin.Goal()
#                 spin_goal.target_yaw = 6.283 # 360 degrees in radians
#                 self.send_action_sync(self.spin_client, spin_goal)
            
#         self.get_logger().info("Mission Complete. Robot has returned Home.")

#     def send_action_sync(self, client, goal):
#         """Thread-safe synchronous action caller"""
#         if not client.wait_for_server(timeout_sec=5.0):
#             self.get_logger().error("Action server not available!")
#             return

#         future = client.send_goal_async(goal)
#         # We are in a thread, so we can block on the future result safely
#         while rclpy.ok() and not future.done():
#             pass
        
#         goal_handle = future.result()
#         if not goal_handle.accepted:
#             self.get_logger().warn("Goal rejected by server.")
#             return

#         result_future = goal_handle.get_result_async()
#         while rclpy.ok() and not result_future.done():
#             pass
#         return result_future.result()

#     def calculate_waypoints(self, min_x, max_x, min_y, max_y):
#         waypoints = []
#         current_x = min_x
#         going_up = True
        
#         while current_x <= max_x:
#             if going_up:
#                 waypoints.append((current_x, min_y))
#                 waypoints.append((current_x, max_y))
#             else:
#                 waypoints.append((current_x, max_y))
#                 waypoints.append((current_x, min_y))
#             going_up = not going_up
#             current_x += self.sweep_spacing
#         return waypoints

#     def publish_boundary(self, min_x, max_x, min_y, max_y):
#         marker = Marker()
#         marker.header.frame_id = 'map'
#         marker.type = Marker.LINE_STRIP
#         marker.action = Marker.ADD
#         marker.scale.x = 0.05
#         marker.color.r, marker.color.g, marker.color.a = 1.0, 0.5, 1.0
        
#         points = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y), (min_x, min_y)]
#         for x, y in points:
#             p = Point()
#             p.x, p.y, p.z = float(x), float(y), 0.02
#             marker.points.append(p)
#         self.boundary_publisher.publish(marker)

#     def yaw_to_quaternion(self, yaw):
#         q = Quaternion()
#         q.z = math.sin(yaw / 2.0)
#         q.w = math.cos(yaw / 2.0)
#         return q

# def main(args=None):
#     rclpy.init(args=args)
#     node = CoveragePlanner()
#     try:
#         rclpy.spin(node)
#     except KeyboardInterrupt:
#         pass
#     node.destroy_node()
#     rclpy.shutdown()

# if __name__ == '__main__':
#     main()