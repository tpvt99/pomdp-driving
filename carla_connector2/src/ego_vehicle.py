#!/usr/bin/env python2

import random
import math
import numpy as np

import rospy
import tf
from geometry_msgs.msg import Twist, Pose, Point, Quaternion, Vector3, Polygon, Point32, PoseStamped
from nav_msgs.msg import Odometry
from nav_msgs.msg import Path as NavPath
from std_msgs.msg import Float32

from drunc import Drunc
import carla
from network_agent_path import NetworkAgentPath
from peds_unity_system.msg import car_info as CarInfo # panpan
from util import *

import tf2_geometry_msgs
import tf2_ros
import geometry_msgs
import time
from tf import TransformListener
import tf.transformations as tftrans

class EgoVehicle(Drunc):
    def __init__(self):
        super(EgoVehicle, self).__init__()

        # Create path.
        self.path = NetworkAgentPath.rand_path(self, 20, 1.0)
            
        vehicle_bp = random.choice(self.world.get_blueprint_library().filter('vehicle.bmw.*'))
        vehicle_bp.set_attribute('role_name', 'ego_vehicle')
        spawn_position = self.path.get_position()
        spawn_trans = carla.Transform()
        spawn_trans.location.x = spawn_position.x
        spawn_trans.location.y = spawn_position.y
        spawn_trans.location.z = 2.0
        spawn_trans.rotation.yaw = self.path.get_yaw()
        self.actor = self.world.spawn_actor(vehicle_bp, spawn_trans)

        self.cmd_speed = 0
        self.cmd_accel = 0
        self.cmd_steer = 0

        self.cmd_speed_sub = rospy.Subscriber('/cmd_speed', Float32, self.cmd_speed_callback, queue_size=1)
        self.cmd_accel_sub = rospy.Subscriber('/cmd_accel', Float32, self.cmd_accel_callback, queue_size=1)
        self.cmd_steer_sub = rospy.Subscriber('/cmd_steer', Float32, self.cmd_steer_callback, queue_size=1)

        self.odom_broadcaster = tf.TransformBroadcaster()
        self.odom_pub = rospy.Publisher('/odom', Odometry, queue_size=1)
        self.car_info_pub = rospy.Publisher('/IL_car_info', CarInfo, queue_size=1)
        self.plan_pub = rospy.Publisher('/plan', NavPath, queue_size=1)

        print("Publish odom static_transform")
        self.broadcaster = None
        self.publish_odom_transform()
        self.transformer = TransformListener()
        
        self.world.on_tick(self.world_tick_callback)
        self.update_timer = rospy.Timer(
                rospy.Duration(0.1), 
                self.update_timer_callback)

    def get_position(self):
        location = self.actor.get_location()
        return carla.Vector2D(location.x, location.y)

    def get_cur_ros_pose(self):
        cur_pose = geometry_msgs.msg.PoseStamped()
        # cur_pose = geometry_msgs.msg.TransformStamped()
   
        cur_pose.header.stamp = rospy.Time.now()
        cur_pose.header.frame_id = "/map"
  
        cur_pose.pose.position.x = self.actor.get_location().x
        cur_pose.pose.position.y = self.actor.get_location().y
        cur_pose.pose.position.z = self.actor.get_location().z
  
        quat = tf.transformations.quaternion_from_euler(
                float(0),float(0),float(np.deg2rad(self.actor.get_transform().rotation.yaw)))
        cur_pose.pose.orientation.x = quat[0]
        cur_pose.pose.orientation.y = quat[1]
        cur_pose.pose.orientation.z = quat[2]
        cur_pose.pose.orientation.w = quat[3]

        return cur_pose
    
    def get_cur_ros_transform(self):
        transformStamped = geometry_msgs.msg.TransformStamped()
   
        transformStamped.header.stamp = rospy.Time.now()
        transformStamped.header.frame_id = "map"
        transformStamped.child_frame_id = 'odom'
  
        transformStamped.transform.translation.x = self.actor.get_location().x
        transformStamped.transform.translation.y = self.actor.get_location().y
        transformStamped.transform.translation.z = self.actor.get_location().z
  
        quat = tf.transformations.quaternion_from_euler(
                float(0),float(0),float(self.actor.get_transform().rotation.yaw))
        transformStamped.transform.rotation.x = quat[0]
        transformStamped.transform.rotation.y = quat[1]
        transformStamped.transform.rotation.z = quat[2]
        transformStamped.transform.rotation.w = quat[3]

        return transformStamped    

    def publish_odom_transform(self):
        self.broadcaster = tf2_ros.StaticTransformBroadcaster()

        static_transformStamped = self.get_cur_ros_transform()
        
        self.broadcaster.sendTransform(static_transformStamped)

        time.sleep(1)

    def get_transform_wrt_odom_frame(self):
        # Wait for odom frame to be ready
        has_odom = False
        while (not has_odom):
            try:
                (trans, rot) = self.transformer.lookupTransform("map", "odom", rospy.Time(0))
                has_odom = True
            except:
                print("odom map transform not exist yet")
                time.sleep(1)

        cur_pose = self.get_cur_ros_pose()

        transform = tftrans.concatenate_matrices(
            tftrans.translation_matrix(trans), tftrans.quaternion_matrix(rot))
        inversed_transform = tftrans.inverse_matrix(transform)

        inv_translation = tftrans.translation_from_matrix(inversed_transform)
        inv_quaternion = tftrans.quaternion_from_matrix(inversed_transform)

        transformStamped = geometry_msgs.msg.TransformStamped()
        transformStamped.transform.translation.x = inv_translation[0]
        transformStamped.transform.translation.y = inv_translation[1]
        transformStamped.transform.translation.z = inv_translation[2]
        transformStamped.transform.rotation.x = inv_quaternion[0]
        transformStamped.transform.rotation.y = inv_quaternion[1]
        transformStamped.transform.rotation.z = inv_quaternion[2]
        transformStamped.transform.rotation.w = inv_quaternion[3]

        cur_transform_wrt_odom = tf2_geometry_msgs.do_transform_pose(
            cur_pose, transformStamped)
        
        translation = cur_transform_wrt_odom.pose.position

        quaternion = (
                cur_transform_wrt_odom.pose.orientation.x,
                cur_transform_wrt_odom.pose.orientation.y,
                cur_transform_wrt_odom.pose.orientation.z,
                cur_transform_wrt_odom.pose.orientation.w)

        _, _, yaw = tf.transformations.euler_from_quaternion(quaternion)   

        return translation, yaw

    def publish_odom(self):
        current_time = rospy.Time.now() 

        frame_id = "odom"
        child_frame_id = "base_link"

        translation, yaw = self.get_transform_wrt_odom_frame()
        pos = carla.Location(translation.x, translation.y, translation.z)
        vel = self.actor.get_velocity()
        v_2d = np.array([vel.x, vel.y, 0])
        forward = np.array([math.cos(np.deg2rad(yaw)), math.sin(np.deg2rad(yaw)), 0])
        speed = np.vdot(forward, v_2d)
        odom_quat = tf.transformations.quaternion_from_euler(0, 0, np.deg2rad(yaw))
        w_yaw = self.actor.get_angular_velocity().z

        self.odom_broadcaster.sendTransform(
            (pos.x, pos.y, pos.z),
            odom_quat,
            current_time,
            child_frame_id,
            frame_id
        )

        odom = Odometry()
        odom.header.stamp = current_time
        odom.header.frame_id = frame_id
        odom.pose.pose = Pose(Point(pos.x, pos.y, 0), Quaternion(*odom_quat))
        odom.child_frame_id = child_frame_id
        odom.twist.twist = Twist(Vector3(vel.x, vel.y, vel.z), Vector3(0, 0, w_yaw))
        self.odom_pub.publish(odom)
    
    def publish_il_car_info(self):
        car_info_msg = CarInfo()

        pos = self.actor.get_location()
        vel = self.actor.get_velocity()
        yaw = self.actor.get_transform().rotation.yaw
        v_2d = np.array([vel.x, vel.y, 0])
        forward = np.array([math.cos(np.deg2rad(yaw)), math.sin(np.deg2rad(yaw)), 0])
        speed = np.vdot(forward, v_2d)
        
        car_info_msg.car_pos.x = pos.x
        car_info_msg.car_pos.y = pos.y
        car_info_msg.car_pos.z = 0
        car_info_msg.car_yaw = yaw
        car_info_msg.car_speed = speed
        car_info_msg.car_steer = self.actor.get_control().steer             
        car_info_msg.car_vel.x = vel.x
        car_info_msg.car_vel.y = vel.y
        car_info_msg.car_vel.z = vel.z
            
        car_info_msg.car_bbox = Polygon()
        corners = get_bounding_box_corners(self.actor)
        for corner in corners:
            car_info_msg.car_bbox.points.append(Point32(
                x=corner.x, y=corner.y, z=0.0))

        self.car_info_pub.publish(car_info_msg)

    def publish_plan(self):
        current_time = rospy.Time.now()

        gui_path = NavPath()
        gui_path.header.frame_id = 'map'
        gui_path.header.stamp = current_time

        # Exclude last point because no yaw information.
        for i in range(len(self.path.route_points) - 1):
            position = self.path.get_position(i)
            yaw = self.path.get_yaw(i)

            pose = PoseStamped()
            pose.header.frame_id = 'map'
            pose.header.stamp = current_time
            pose.pose.position.x = position.x
            pose.pose.position.y = position.y
            pose.pose.position.z = 0
            quaternion = tf.transformations.quaternion_from_euler(0, 0, yaw)
            pose.pose.orientation.x = quaternion[0]
            pose.pose.orientation.y = quaternion[1]
            pose.pose.orientation.z = quaternion[2]
            pose.pose.orientation.w = quaternion[3]
            gui_path.poses.append(pose)
        
        self.plan_pub.publish(gui_path)

    def cmd_speed_callback(self, speed):
        self.cmd_speed = speed.data

    def cmd_accel_callback(self, accel):
        self.cmd_accel = accel.data

    def cmd_steer_callback(self, steer):
        self.cmd_steer = steer.data

    def world_tick_callback(self, snapshot):
        if not self.path.resize():
            print('Warning : path too short.')
            return

        self.path.cut(self.get_position())
        
        if not self.path.resize():
            print('Warning : path too short.')
            return

        self.publish_odom()
        self.publish_il_car_info()
        self.publish_plan()

    def update_timer_callback(self, timer):
        # Calculate control and send to CARLA.
        
        control = self.actor.get_control()
        control.gear = 1 
        control.steer = self.cmd_steer
        if self.cmd_accel > 0:
            control.throttle = self.cmd_accel
            control.brake = 0.0
        elif self.cmd_accel == 0:
            control.throttle = 0.0
            control.brake = 0.0
        else:
            control.throttle = 0.0
            control.brake = self.cmd_accel

        self.actor.apply_control(control)

if __name__ == '__main__':
    rospy.init_node('ego_vehicle')
    ego_vehicle = EgoVehicle()
    rospy.spin()
