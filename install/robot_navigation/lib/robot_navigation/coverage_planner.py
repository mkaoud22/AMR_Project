#!/usr/bin/env python3

# import rclpy
# from rclpy.node import Node
# from rclpy.action import ActionClient
# from rclpy.qos import QoSProfile, DurabilityPolicy
# from geometry_msgs.msg import PointStamped, PoseStamped, Quaternion, Point
# from nav_msgs.msg import Path
# from nav2_msgs.action import NavigateToPose
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
#         self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
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
from geometry_msgs.msg import PolygonStamped, PoseStamped, Quaternion, Point
from nav_msgs.msg import Path
from nav2_msgs.action import NavigateToPose
from visualization_msgs.msg import Marker
from std_msgs.msg import Empty
import math

# NEW: Import TF2 modules to get the robot's current position
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

class CoveragePlanner(Node):
    def __init__(self):
        super().__init__('coverage_planner')
        
        # Subscribers and Publishers
        self.subscription = self.create_subscription(PolygonStamped, '/coverage_polygon', self.polygon_callback, 10)
        self.nogo_subscription = self.create_subscription(PolygonStamped, '/nogo_zone', self.nogo_callback, 10)
        self.stop_subscription = self.create_subscription(Empty, '/stop_and_dock', self.stop_and_dock_callback, 10)
        # Use transient local (latched) QoS so the path persists and shows immediately in RViz
        self.vis_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.path_publisher = self.create_publisher(Path, '/coverage_path', self.vis_qos)
        self.boundary_publisher = self.create_publisher(Marker, '/coverage_boundary', self.vis_qos)
        
        # Action Client for Nav2
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        # Sequential navigation queue variables
        self.poses_queue = []
        self.current_pose_index = 0
        self.current_goal_handle = None
        self.is_cleaning = False
        
        # NEW: Initialize the TF2 buffer and listener
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        self.clicked_points = []
        self.nogo_points = []
        
        self.pose_publisher = self.create_publisher(PoseStamped, '/robot_pose', 10)
        self.pose_timer = self.create_timer(0.1, self.publish_robot_pose)
        
        # UPDATE: Vacuum tool width set to 480mm (0.48m)
        self.sweep_spacing = 0.48 
        
        self.get_logger().info("Coverage Planner ready. Waiting for mobile app polygons.")

    def publish_robot_pose(self):
        try:
            t = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
            pose_msg = PoseStamped()
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.header.frame_id = 'map'
            pose_msg.pose.position.x = t.transform.translation.x
            pose_msg.pose.position.y = t.transform.translation.y
            pose_msg.pose.position.z = t.transform.translation.z
            pose_msg.pose.orientation = t.transform.rotation
            self.pose_publisher.publish(pose_msg)
        except TransformException:
            pass

    def nogo_callback(self, msg):
        self.nogo_points = msg.polygon.points
        self.get_logger().info(f"Received no-go zone with {len(self.nogo_points)} points.")
        if len(self.nogo_points) >= 3:
            self.publish_nogo_boundary()

    def polygon_callback(self, msg):
        self.clicked_points = msg.polygon.points
        self.get_logger().info(f"Received coverage polygon with {len(self.clicked_points)} points.")

        if len(self.clicked_points) >= 3:
            self.get_logger().info("Calculating path and boundary...")
            self.generate_and_execute_path()
        else:
            self.get_logger().warn("Received polygon with fewer than 3 points. Ignoring.")

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
            # Look up the transform from base_footprint to map
            t = self.tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
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

        has_nogo = False
        nogo_min_x, nogo_max_x = 0.0, 0.0
        nogo_min_y, nogo_max_y = 0.0, 0.0
        margin = 0.30  # Safety buffer margin in meters
        
        if len(self.nogo_points) >= 3:
            has_nogo = True
            nogo_x = [p.x for p in self.nogo_points]
            nogo_y = [p.y for p in self.nogo_points]
            nogo_min_x, nogo_max_x = min(nogo_x), max(nogo_x)
            nogo_min_y, nogo_max_y = min(nogo_y), max(nogo_y)
            
            # Apply safety margin to the no-go zone boundaries and clamp within coverage bounds
            nogo_min_x_m = max(min_x, nogo_min_x - margin)
            nogo_max_x_m = min(max_x, nogo_max_x + margin)
            nogo_min_y_m = max(min_y, nogo_min_y - margin)
            nogo_max_y_m = min(max_y, nogo_max_y + margin)
            
            # Choose the side of the no-go zone with more clearance to bypass
            left_clearance = nogo_min_x - min_x
            right_clearance = max_x - nogo_max_x
            if left_clearance > right_clearance:
                bypass_x = max(min_x, nogo_min_x - margin)
            else:
                bypass_x = min(max_x, nogo_max_x + margin)

        while end_condition(current_x):
            intersects_nogo = False
            if has_nogo:
                # Column intersects if its X coordinate is within the buffered X range of the no-go zone
                if nogo_min_x_m <= current_x <= nogo_max_x_m:
                    intersects_nogo = True

            if intersects_nogo:
                if going_up:
                    # Sweep lower part of column
                    waypoints.append((current_x, min_y))
                    waypoints.append((current_x, nogo_min_y_m))
                    
                    # Bypass around the no-go zone
                    waypoints.append((bypass_x, nogo_min_y_m))
                    waypoints.append((bypass_x, nogo_max_y_m))
                    
                    # Sweep upper part of column
                    waypoints.append((current_x, nogo_max_y_m))
                    waypoints.append((current_x, max_y))
                else:
                    # Sweep upper part of column
                    waypoints.append((current_x, max_y))
                    waypoints.append((current_x, nogo_max_y_m))
                    
                    # Bypass around the no-go zone
                    waypoints.append((bypass_x, nogo_max_y_m))
                    waypoints.append((bypass_x, nogo_min_y_m))
                    
                    # Sweep lower part of column
                    waypoints.append((current_x, nogo_min_y_m))
                    waypoints.append((current_x, min_y))
            else:
                # Standard full-column sweep
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

        # Publish Path, Path Marker and Send to Nav2
        self.path_publisher.publish(path_msg)
        self.publish_path_marker(waypoints)
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

    def publish_nogo_boundary(self):
        if not self.nogo_points:
            return
        x_coords = [p.x for p in self.nogo_points]
        y_coords = [p.y for p in self.nogo_points]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        marker = Marker()
        marker.header.frame_id = 'map'
        marker.header.stamp.sec = 0
        marker.header.stamp.nanosec = 0
        marker.ns = 'nogo_zone'
        marker.id = 2
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        
        marker.pose.orientation.w = 1.0 
        
        marker.scale.x = 0.05 
        marker.scale.y = 0.05
        marker.scale.z = 0.05
        
        # Red color
        marker.color.r = 1.0
        marker.color.g = 0.0
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


    def publish_path_marker(self, waypoints):
        marker = Marker()
        marker.header.frame_id = 'map'
        marker.header.stamp.sec = 0
        marker.header.stamp.nanosec = 0
        marker.ns = 'coverage_path'
        marker.id = 1
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        
        marker.pose.orientation.w = 1.0 
        
        marker.scale.x = 0.05  # Line width of 5cm
        
        # Solid Blue Color (matches the second photo)
        marker.color.r = 0.0
        marker.color.g = 0.4
        marker.color.b = 1.0
        marker.color.a = 1.0
        
        for x, y in waypoints:
            p = Point()
            p.x = float(x)
            p.y = float(y)
            p.z = 0.02  # slightly off the ground to avoid z-fighting with the grid map
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
        
        self.poses_queue = poses
        self.current_pose_index = 0
        self.is_cleaning = True
        self.send_next_pose_goal()

    def send_next_pose_goal(self):
        if not self.is_cleaning or self.current_pose_index >= len(self.poses_queue):
            self.get_logger().info('Coverage task finished! Returning to dock.')
            self.is_cleaning = False
            self.return_to_dock()
            return

        pose = self.poses_queue[self.current_pose_index]
        self.get_logger().info(f"Navigating to waypoint {self.current_pose_index + 1}/{len(self.poses_queue)}: X: {pose.pose.position.x:.2f}, Y: {pose.pose.position.y:.2f}")
        
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose

        self.send_goal_future = self.nav_client.send_goal_async(goal_msg)
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error(f'Goal for waypoint {self.current_pose_index + 1} rejected by Nav2 server.')
            self.is_cleaning = False
            self.return_to_dock()
            return
        
        self.current_goal_handle = goal_handle
        self.get_logger().info(f'Waypoint {self.current_pose_index + 1} accepted. Executing...')
        self.get_result_future = goal_handle.get_result_async()
        self.get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        if not self.is_cleaning:
            return
        
        self.get_logger().info(f'Reached waypoint {self.current_pose_index + 1}.')
        self.current_goal_handle = None
        self.current_pose_index += 1
        self.send_next_pose_goal()

    def stop_and_dock_callback(self, msg):
        self.get_logger().info('Received stop command! Aborting coverage and returning to dock.')
        self.is_cleaning = False
        self.poses_queue = []
        if self.current_goal_handle is not None:
            self.get_logger().info('Canceling current active navigation goal...')
            self.current_goal_handle.cancel_goal_async()
            self.current_goal_handle = None
        self.return_to_dock()

    def return_to_dock(self):
        self.get_logger().info("Waiting for Nav2 server to return to dock...")
        self.nav_client.wait_for_server()

        dock_pose = PoseStamped()
        dock_pose.header.frame_id = 'map'
        dock_pose.header.stamp = self.get_clock().now().to_msg()
        dock_pose.pose.position.x = 3.355494   
        dock_pose.pose.position.y = -0.881754  
        dock_pose.pose.position.z = 0.0        
        dock_pose.pose.orientation = self.yaw_to_quaternion(-0.020110) 

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = dock_pose
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
