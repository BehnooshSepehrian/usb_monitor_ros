#!/usr/bin/env python

"""
mount_point_tracker.py

This module creates the MountPoint class which is responsible to manage the mount point
that is created when the USB is plugged in. This provides functionality to mount/unmount
the filesystem, increment/decrement reference counters to it.
"""

import os
import subprocess
import shutil
import rospy

from usb_monitor import constants


#########################################################################################
# Mount point tracker.


class MountPoint:
    """Class which is responsible to manage the mount points.
    """
    def __init__(self, node_name, post_action=None):
        """Create a MountPoint object.

        Args:
            node_name (str): Source filesystem type to be mounted.
            logger (rclpy.rclpy.impl.rcutils_logger.RcutilsLogger):
                Logger object of the usb_monitor_node.
            post_action (function, optional): Function that needs to be executed as part of
                                              post_action list. Defaults to None.
        """
        self.post_action = list()
        self.name = self.mount(node_name)
        if self.name == "":
            self.ref = 0
        else:
            self.ref = 1
        self.add_post_action(post_action)

    def is_valid(self):
        """Check for mount point validity.

        Returns:
            bool: True if valid else False.
        """
        return (self.name != "") and (self.ref > 0)

    def ref_inc(self):
        """Helper function to increment the reference counter.
        """
        self.ref += 1

    def ref_dec(self):
        """Helper function to decrement the reference counter and unmount filesystem if 0.
        """
        self.ref -= 1
        if (self.ref == 0) and (self.name != ""):
            if self.umount_filesystem(self.name):
                rospy.loginfo("Unmounted %s",self.name)
            self.name = ""
            for action in self.post_action:
                action()
            self.post_action = list()

    def add_post_action(self, post_action):
        """Add a function to be executed on decrementing the reference to the mount point.

        Args:
            post_action (function): Function type to be added to the post_action list.
        """
        if (post_action is not None) and (post_action not in self.post_action):
            self.post_action.append(post_action)

    def mount(self, source):
        """Helper function to mount all the devices of a particular filesystem.

        Args:
            source (str): Filesystem type to be mounted.

        Returns:
            str: Custom mount point name created.
        """
        # Get all existing mount points of the source.
        existing_mount_points = self.get_mount_points(source)

        # Build our mount point name.
        mount_point = "{0}-{1}".format(constants.BASE_MOUNT_POINT,os.path.basename(source))

        # Don"t mount if already mounted.
        if mount_point in existing_mount_points:
            rospy.loginfo("%s is already mounted to %s",source,mount_point)

        else:
            if not self.mount_filesystem(source, mount_point):
                return ""

            rospy.loginfo("Mounted %s to %s",source,mount_point)

        return mount_point

    def get_mount_points(self, filesystem):
        """Return the list of mount points.

        Args:
            filesystem (str): Filesystem type to be mounted.

        Returns:
            list: List of mount points.
        """
        mount_points = list()

        try:
            with open(os.path.join(os.sep, "proc", "mounts")) as mount_list:
                for line in mount_list:
                    components = line.strip().split()
                    if len(components) < 2:
                        continue

                    _filesystem = components[0].strip()
                    mount_point = components[1].strip()

                    if _filesystem == filesystem:
                        mount_points.append(mount_point)
        except Exception:
            pass

        return mount_points

    def mount_filesystem(self, source, target):
        """Helper function to execute mount command to mount the source filesystem to
           target filesystem.

        Args:
            source (str): Filesystem type mounted.
            target (str): Filepath to the target filesystem.

        Returns:
            bool: True if successful else False.
        """
        try:
            if not os.path.isdir(target):
                os.makedirs(target)
        except Exception as ex:
            return False

        p = subprocess.Popen(["mount", source, target],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (out,err)=p.communicate()
        if p.returncode != 0:
            shutil.rmtree(target)
            rospy.logerr("Failed to mount %s to %s, error code = %d  : %s", 
                            source,
                            target,
                            p.returncode,err)
            return False

        return True

    def umount_filesystem(self, target):
        """Helper function to execute the unmount command on the target.

        Args:
            target (str): Filepath to the mounted filesystem.

        Returns:
            bool: True if successful else False.
        """
        p = subprocess.Popen(["umount", target],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        p.communicate()
        if p.returncode != 0:
            rospy.logerr("Failed to unmount %s",target)
            return False

        shutil.rmtree(target)
        return True
