import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro

def generate_launch_description():

    ##use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    urdf_file_name = 'robot.urdf.xacro'
    package_name = "diff_robot"
    
    urdf = os.path.join(get_package_share_directory(package_name),"urdf",urdf_file_name)
    xacro_file = xacro.process_file(urdf)

    urdf_content = open(urdf).read()
    robot_state_publisher_node = Node( package='robot_state_publisher', executable='robot_state_publisher', name='robot_state_publisher', parameters=[{'use_sim_time': True,'robot_description':  xacro_file.toxml()}], output='screen'

    )

        # joint State Publisher
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher_node',
        output="screen"
    )

    return LaunchDescription(
        [
            robot_state_publisher_node,
            # joint_state_publisher_node
        ]
    ) 