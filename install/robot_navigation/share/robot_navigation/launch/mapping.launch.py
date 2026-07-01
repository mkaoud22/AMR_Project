import os

# ---> NEW: Import ament_index_python to find your package path dynamically
from ament_index_python.packages import get_package_share_directory 

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Dynamically find the path to your config file
    
    pkg_share = get_package_share_directory('robot_navigation')
    
    # We usually keep config files in a 'config' folder inside the package.
    mapping_config_file = os.path.join(pkg_share, 'config', 'mapper_params_localization.yaml')

    # 2. Create variables for launch configurations
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    # 3. Declare the launch arguments
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo/Ignition) clock if true'
    )

    declare_cmd_vel_topic = DeclareLaunchArgument(
        'cmd_vel_topic',
        default_value='/cmd_vel',
        description='Topic to publish cmd_vel to (e.g., /cmd_vel or /diff_cont/cmd_vel_unstamped)'
    )

    # 4. Define the SLAM Toolbox Node
    start_async_slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            mapping_config_file # <--- This will now resolve to the correct, absolute path
        ]
    )

    # 5. Define the RViz2 Node 
    start_rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen'
    )

    # 6. Define the Teleop Twist Keyboard Node
    start_teleop_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        prefix='xterm -e',
        remappings=[
            ('/cmd_vel', LaunchConfiguration('cmd_vel_topic'))
        ]
    )

    # 7. Build and return the Launch Description
    ld = LaunchDescription()

    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_cmd_vel_topic)
    ld.add_action(start_async_slam_toolbox_node)
    ld.add_action(start_rviz2_node) 
    ld.add_action(start_teleop_node)

    return ld