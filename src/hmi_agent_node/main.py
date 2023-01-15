#!/usr/bin/env python3

import rospy
from dataclasses import dataclass
from rio_control_node.msg import Joystick_Status, Robot_Status
from ck_ros_msgs_node.msg import HMI_Signals
from ck_utilities_py_node.joystick import Joystick
from ck_utilities_py_node.ckmath import *
import numpy as np

@dataclass
class DriveParams:
    drive_fwd_back_axis_id: int = -1
    drive_fwd_back_axis_inverted: bool = False
    drive_left_right_axis_id: int = -1
    drive_left_right_axis_inverted: bool = False
    drive_z_axis_id: int = -1
    drive_z_axis_inverted: bool = False
    drive_axis_deadband: float = 0.05
    drive_z_axis_deadband: float = 0.05

    drive_brake_button_id: int = -1
    drive_quickturn_button_id: int = -1


drive_params = DriveParams()

hmi_pub = rospy.Publisher(
    name="/HMISignals", data_class=HMI_Signals, queue_size=10, tcp_nodelay=True)

drive_joystick = Joystick(0)
arm_joystick = Joystick(1)
bb1_joystick = Joystick(2)
bb2_joystick = Joystick(3)

is_auto = False


def robot_status_callback(msg: Robot_Status):
    global is_auto
    is_auto = (msg.robot_state == msg.AUTONOMOUS)


def joystick_callback(msg: Joystick_Status):
    global is_auto
    global hmi_pub
    global drive_joystick
    global arm_joystick
    global bb1_joystick
    global bb2_joystick
    global params
    Joystick.update(msg)

    hmi_update_msg = HMI_Signals()

    hmi_update_msg.drivetrain_brake = drive_joystick.getButton(
        drive_params.drive_brake_button_id)

    invert_axis_fwd_back = -1 if drive_params.drive_fwd_back_axis_inverted else 1
    invert_axis_left_right = -1 if drive_params.drive_left_right_axis_inverted else 1

    hmi_update_msg.drivetrain_fwd_back = invert_axis_fwd_back * \
        drive_joystick.getFilteredAxis(
            drive_params.drive_fwd_back_axis_id, drive_params.drive_axis_deadband)

    hmi_update_msg.drivetrain_left_right = invert_axis_left_right * \
        drive_joystick.getFilteredAxis(
            drive_params.drive_left_right_axis_id, drive_params.drive_axis_deadband)

    x = hmi_update_msg.drivetrain_fwd_back
    y = hmi_update_msg.drivetrain_left_right
    invert_axis_z = -1 if drive_params.drive_z_axis_inverted else 1
    z = invert_axis_z * drive_joystick.getFilteredAxis(
        drive_params.drive_z_axis_id, drive_params.drive_z_axis_deadband)

    r = hypotenuse(x, y)
    theta = polar_angle_rad(x, y)

    z = np.sign(z) * pow(z, 2)
    active_theta = theta
    if (r > drive_params.drive_axis_deadband):
        active_theta = theta

    hmi_update_msg.drivetrain_swerve_direction = active_theta
    hmi_update_msg.drivetrain_swerve_percent_fwd_vel = limit(r, 0.0, 1.0)
    hmi_update_msg.drivetrain_swerve_percent_angular_rot = z

    hmi_pub.publish(hmi_update_msg)


def init_params():
    global drive_params

    drive_params.drive_fwd_back_axis_id = rospy.get_param(
        "drive_fwd_back_axis_id", -1)
    drive_params.drive_fwd_back_axis_inverted = rospy.get_param(
        "drive_fwd_back_axis_inverted", -1)

    drive_params.drive_turn_axis_id = rospy.get_param("drive_turn_axis_id", -1)
    drive_params.drive_turn_axis_inverted = rospy.get_param(
        "drive_turn_axis_inverted", -1)


def ros_main(node_name):
    rospy.init_node(node_name)
    init_params()
    rospy.Subscriber(name="/JoystickStatus", data_class=Joystick_Status,
                     callback=joystick_callback, queue_size=1, tcp_nodelay=True)
    rospy.Subscriber(name="/RobotStatus", data_class=Robot_Status,
                     callback=robot_status_callback, queue_size=1, tcp_nodelay=True)
    rospy.spin()
