#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Quaternion
import math
import time

try:
    import smbus2 as smbus
except ImportError:
    try:
        import smbus
    except ImportError:
        smbus = None

# MPU6500 Register Map
PWR_MGMT_1 = 0x6B
CONFIG = 0x1A
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

class MPU6500Node(Node):
    def __init__(self):
        super().__init__('mpu6500_node')

        self.declare_parameter('i2c_bus', 1)
        self.declare_parameter('i2c_address', 0x68)
        self.declare_parameter('frame_id', 'imu_frame')
        self.declare_parameter('publish_rate', 50.0)

        self.i2c_bus_num = self.get_parameter('i2c_bus').value
        self.i2c_address = self.get_parameter('i2c_address').value
        self.frame_id = self.get_parameter('frame_id').value
        self.publish_rate = self.get_parameter('publish_rate').value

        self.publisher_ = self.create_publisher(Imu, '/imu/data', 10)

        self.bus = None
        self.hardware_available = False

        if smbus is None:
            self.get_logger().error("smbus2/smbus module not found! Please install with 'pip install smbus2' or 'sudo apt install python3-smbus2'.")
        else:
            try:
                self.bus = smbus.SMBus(self.i2c_bus_num)
                self.init_mpu6500()
                self.hardware_available = True
                self.get_logger().info(f"MPU6500 initialized successfully on I2C bus {self.i2c_bus_num} at address {hex(self.i2c_address)}.")
            except Exception as e:
                self.get_logger().warn(f"Could not open I2C bus {self.i2c_bus_num} at {hex(self.i2c_address)}: {e}. Running in dummy/fallback mode.")

        # Gyro offsets
        self.gyro_offset_x = 0.0
        self.gyro_offset_y = 0.0
        self.gyro_offset_z = 0.0

        if self.hardware_available:
            self.calibrate_gyro()

        # Orientation state
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.last_time = self.get_clock().now()

        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def write_byte(self, reg, value):
        self.bus.write_byte_data(self.i2c_address, reg, value)

    def read_word(self, reg):
        high = self.bus.read_byte_data(self.i2c_address, reg)
        low = self.bus.read_byte_data(self.i2c_address, reg + 1)
        val = (high << 8) + low
        if val >= 0x8000:
            return -((65535 - val) + 1)
        else:
            return val

    def init_mpu6500(self):
        # Reset and wake up MPU6500 (clock source PLL with X gyro ref)
        self.write_byte(PWR_MGMT_1, 0x01)
        time.sleep(0.05)

        # Set DLPF (Digital Low Pass Filter) to ~41Hz
        self.write_byte(CONFIG, 0x03)

        # Gyro scale: +-250 deg/s (0x00) -> 131.0 LSB/(deg/s)
        self.write_byte(GYRO_CONFIG, 0x00)

        # Accel scale: +-2g (0x00) -> 16384 LSB/g
        self.write_byte(ACCEL_CONFIG, 0x00)

    def calibrate_gyro(self, samples=200):
        self.get_logger().info("Calibrating MPU6500 gyroscope... Keep the robot stationary.")
        sum_x, sum_y, sum_z = 0.0, 0.0, 0.0
        valid_samples = 0

        for _ in range(samples):
            try:
                gx = self.read_word(GYRO_XOUT_H)
                gy = self.read_word(GYRO_XOUT_H + 2)
                gz = self.read_word(GYRO_XOUT_H + 4)
                sum_x += gx
                sum_y += gy
                sum_z += gz
                valid_samples += 1
                time.sleep(0.005)
            except Exception:
                pass

        if valid_samples > 0:
            self.gyro_offset_x = (sum_x / valid_samples) / 131.0 * (math.pi / 180.0)
            self.gyro_offset_y = (sum_y / valid_samples) / 131.0 * (math.pi / 180.0)
            self.gyro_offset_z = (sum_z / valid_samples) / 131.0 * (math.pi / 180.0)
            self.get_logger().info(f"Gyro calibration complete. Offsets rad/s: X={self.gyro_offset_x:.4f}, Y={self.gyro_offset_y:.4f}, Z={self.gyro_offset_z:.4f}")

    def timer_callback(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        if dt <= 0.0 or dt > 0.5:
            dt = 1.0 / self.publish_rate

        ax_m_s2, ay_m_s2, az_m_s2 = 0.0, 0.0, 9.80665
        gx_rad, gy_rad, gz_rad = 0.0, 0.0, 0.0

        if self.hardware_available:
            try:
                # Read raw accelerometer
                ax_raw = self.read_word(ACCEL_XOUT_H)
                ay_raw = self.read_word(ACCEL_XOUT_H + 2)
                az_raw = self.read_word(ACCEL_XOUT_H + 4)

                # Read raw gyroscope
                gx_raw = self.read_word(GYRO_XOUT_H)
                gy_raw = self.read_word(GYRO_XOUT_H + 2)
                gz_raw = self.read_word(GYRO_XOUT_H + 4)

                # Convert to standard units
                # Accel scale +-2g: 16384 LSB / g
                ax_m_s2 = (ax_raw / 16384.0) * 9.80665
                ay_m_s2 = (ay_raw / 16384.0) * 9.80665
                az_m_s2 = (az_raw / 16384.0) * 9.80665

                # Gyro scale +-250 dps: 131 LSB / (deg/s)
                gx_rad = (gx_raw / 131.0) * (math.pi / 180.0) - self.gyro_offset_x
                gy_rad = (gy_raw / 131.0) * (math.pi / 180.0) - self.gyro_offset_y
                gz_rad = (gz_raw / 131.0) * (math.pi / 180.0) - self.gyro_offset_z

            except Exception as e:
                self.get_logger().error(f"Error reading MPU6500 sensor: {e}")

        # Integrate yaw from gyro
        self.yaw += gz_rad * dt

        # Roll and Pitch from accelerometer (for stationary alignment)
        accel_roll = math.atan2(ay_m_s2, az_m_s2)
        accel_pitch = math.atan2(-ax_m_s2, math.sqrt(ay_m_s2**2 + az_m_s2**2))

        # Complementary filter for roll and pitch
        alpha = 0.96
        self.roll = alpha * (self.roll + gx_rad * dt) + (1 - alpha) * accel_roll
        self.pitch = alpha * (self.pitch + gy_rad * dt) + (1 - alpha) * accel_pitch

        # Convert Euler (roll, pitch, yaw) to Quaternion
        qx, qy, qz, qw = self.euler_to_quaternion(self.roll, self.pitch, self.yaw)

        # Build ROS 2 Imu message
        msg = Imu()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = self.frame_id

        msg.orientation.x = qx
        msg.orientation.y = qy
        msg.orientation.z = qz
        msg.orientation.w = qw
        msg.orientation_covariance = [0.01, 0.0, 0.0,
                                       0.0, 0.01, 0.0,
                                       0.0, 0.0, 0.05]

        msg.angular_velocity.x = gx_rad
        msg.angular_velocity.y = gy_rad
        msg.angular_velocity.z = gz_rad
        msg.angular_velocity_covariance = [0.0001, 0.0, 0.0,
                                            0.0, 0.0001, 0.0,
                                            0.0, 0.0, 0.0001]

        msg.linear_acceleration.x = ax_m_s2
        msg.linear_acceleration.y = ay_m_s2
        msg.linear_acceleration.z = az_m_s2
        msg.linear_acceleration_covariance = [0.01, 0.0, 0.0,
                                               0.0, 0.01, 0.0,
                                               0.0, 0.0, 0.01]

        self.publisher_.publish(msg)

    def euler_to_quaternion(self, r, p, y):
        cy = math.cos(y * 0.5)
        sy = math.sin(y * 0.5)
        cp = math.cos(p * 0.5)
        sp = math.sin(p * 0.5)
        cr = math.cos(r * 0.5)
        sr = math.sin(r * 0.5)

        qw = cr * cp * cy + sr * sp * sy
        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy

        return qx, qy, qz, qw

def main(args=None):
    rclpy.init(args=args)
    node = MPU6500Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
