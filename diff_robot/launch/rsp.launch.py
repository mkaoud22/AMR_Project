
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():

    ##use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    urdf_file_name = 'robot.urdf'
    package_name = "diff_robot"
    
    urdf = os.path.join(get_package_share_directory(package_name),"urdf",urdf_file_name)
    

    urdf_content = open(urdf).read()

    robot_state_publisher_node = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{'use_sim_time': True, 'robot_description':  urdf_content }],
            output='screen'

    )

    return LaunchDescription(
        [
            robot_state_publisher_node
        ]
    ) 