from launch import LaunchDescription
from ament_index_python import get_package_share_directory
from launch_ros.actions import Node
import os

from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    package_name = "robot_navigation"
    config_dir = os.path.join(get_package_share_directory(package_name), "config")
    localization_config_file = 'amcl_config.yaml'
    map_file = "home_map.yaml"

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    map_server = Node(

        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[{'use_sim_time': use_sim_time},
                    {"yaml_filename": os.path.join(config_dir, map_file)}],

    )

    localization = Node(
        package="nav2_amcl",
        executable="amcl",
        output="screen",
        name="amcl",
        parameters=[os.path.join(config_dir, localization_config_file), {'use_sim_time': use_sim_time}],

    )

    lifecycle_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name= "lifecycle_node",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}, 
                    {"autostart": True},
                    {'node_names': ["map_server", "amcl"]}]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation (Gazebo) clock if true'
        ),
        map_server,
        localization,
        lifecycle_manager
    ])