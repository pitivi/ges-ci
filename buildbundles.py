#!/usr/bin/python3

import os
import sys
import subprocess
import time


def message(msg):
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()


def call(command):
    message("Running %s" % command)
    return os.system(command) == 0


def bundle(vmname, vmuser, sshadress):
    call("VBoxManage startvm %s --type headless" % vmname)
    vm_is_ready = False
    t = time.time()
    while not call("ssh %s@%s echo 'Vm is up and running'" % (vmuser, sshadress)):
        if time.time() - t > 600:
            message("TIMEOUT, could not connect to VM")
            # call("VBoxManage controlvm %s savestate" % vmname)
            return False

    if not call("ssh %s@%s /home/%s/bin/update_bundle latest" % (vmuser, sshadress, vmuser)):
        message("Update bundle FAILED")
        return False

    # if not call("VBoxManage controlvm %s savestate" % vmname):
    #    message("Save state failed -- not fatal")

    return True

if __name__ == "__main__":
    ret = 0

    for vmname, vmuser, sshadress in (("debian32", "gstqa", "192.168.0.8"),
                                      ("debian64", "gst-qa", "192.168.0.10")):
        if not bundle(vmname, vmuser, sshadress):
            ret = 1
            message("ERROR, Could not create %s bundle" % (vmname))

    exit(ret)
