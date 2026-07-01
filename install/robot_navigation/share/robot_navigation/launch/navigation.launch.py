

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition


def generate_launch_description():
    
    package_name = "robot_navigation"
    
    nav2_yaml = os.path.join(get_package_share_directory(package_name), 'config', 'amcl_config.yaml')
    map_file = os.path.join(get_package_share_directory(package_name), 'config', 'home_map.yaml') #change to your map
    rviz_config_file = os.path.join(get_package_share_directory(package_name), "rviz", "navigation_1.rviz")
    planner_yaml = os.path.join(get_package_share_directory(package_name), 'config', 'planner_server.yaml')
    controller_yaml = os.path.join(get_package_share_directory(package_name), 'config', 'controller.yaml')
    bt_navigator_yaml = os.path.join(get_package_share_directory(package_name), 'config', 'bt_navigator.yaml')
    recovery_yaml = os.path.join(get_package_share_directory(package_name), 'config', 'recovery.yaml')
    # ekf_yaml = os.path.join(get_package_share_directory(package_name), 'config', 'ekf_sensor_fusion.yaml')

    use_rviz = LaunchConfiguration("rviz", default=True)
    
    # Define sim time parameter to easily pass to all nodes
    sim_time = {'use_sim_time': True}
    
    return LaunchDescription([
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[sim_time, {'yaml_filename':map_file}]
        ),
            
        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            output='screen',
            parameters=[nav2_yaml, sim_time]
        ),
        Node(
            package='nav2_controller',
            executable='controller_server',
            name='controller_server',
            output='screen',
            parameters=[controller_yaml, sim_time]),

        Node(
            package='nav2_planner',
            executable='planner_server',
            name='planner_server',
            output='screen',
            parameters=[planner_yaml, sim_time]),
            
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            name='behavior_server',
            parameters=[recovery_yaml, sim_time],
            output='screen'),

        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            name='bt_navigator',
            output='screen',
            parameters=[bt_navigator_yaml, sim_time]),

        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_pathplanner',
            output='screen',
            parameters=[sim_time,
                        {'autostart': True},
                        {'node_names': ['map_server',
                                        'amcl',
                                        'planner_server',
                                        'controller_server',
                                        'behavior_server',
                                        'bt_navigator']}]),
        
        # Node(
        # package='robot_localization',
        # executable='ekf_node',
        # name='ekf_filter_node',
        # output='screen',
        # parameters=[ekf_yaml, sim_time]
        # ),

        Node(
            package='robot_navigation',
            executable='coverage_planner.py',
            name='coverage_planner',
            output='screen',
            parameters=[sim_time] 
        ),
        Node(
            package= "rviz2",
            executable= "rviz2",
            arguments=["-d", rviz_config_file],
            output= "screen",
            parameters=[sim_time], # Added sim time to RViz too!
            condition=IfCondition(use_rviz)),
    ])