import subprocess32
import time
import os
from optparse import OptionParser
from buildgst import bcolors
from gi.repository import GES, Gst
import xml.etree.ElementTree as ET

formats = {"aac": "audio/mpeg,mpegversion=4",
           "ac3": "audio/x-ac3",
           "vorbis": "audio/x-vorbis",
           "mp3": "audio/mpeg,mpegversion=1,layer=3",
           "h264": "video/x-h264",
           "vp8": "video/x-vp8",
           "theora": "video/x-theora",
           "ogg": "application/ogg",
           "mkv": "video/x-matroska",
           "mp4": "video/quicktime,variant=iso;",
           "webm": "video/x-matroska"}


def print_ns(time):
    if time == Gst.CLOCK_TIME_NONE:
        return "CLOCK_TIME_NONE"

    return str(time / (Gst.SECOND * 60 * 60)) + ':' + \
        str((time / (Gst.SECOND * 60)) % 60) + ':' + \
        str((time / Gst.SECOND) % 60) + ':' + \
        str(time % Gst.SECOND)


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class Combination():
    def __str__(self):
        return "%s and %s in %s" % (self.container, self.acodec, self.vcodec)

    def __init__(self, container, acodec, vcodec):
        self.container = container
        self.acodec = acodec
        self.vcodec = vcodec

combinations = [
    Combination("ogg", "vorbis", "theora"),
    Combination("webm", "vorbis", "vp8"),
    Combination("mp4", "mp3", "h264"),
    Combination("mkv", "vorbis", "h264")]


def get_profile_full(muxer, venc, aenc, video_restriction=None,
                     audio_restriction=None,
                     audio_presence=0, video_presence=0):
    ret = "\""
    if muxer:
        ret += muxer
    ret += ":"
    if venc:
        if video_restriction is not None:
            ret = ret + video_restriction + '->'
        ret += venc
        if video_presence:
            ret = ret + '|' + str(video_presence)
    if aenc:
        ret += ":"
        if audio_restriction is not None:
            ret = ret + audio_restriction + '->'
        ret += aenc
        if audio_presence:
            ret = ret + '|' + str(audio_presence)

    ret += "\""
    return ret.replace("::", ":")


def get_profile(combination):
    return get_profile_full(formats[combination.container],
                            formats[combination.vcodec],
                            formats[combination.acodec],
                            video_restriction="video/x-raw,format=I420")


def getDuration(project):

    proj = GES.Project.new(project)
    tl = proj.extract()
    if tl is None:
        duration = None
    else:
        duration = tl.get_meta("duration")
    if duration is not None:
        return duration / Gst.SECOND
    return 10 * 60


def launch_project(project, combination, dest_dir, paths=[], elem=None):
    ret = True

    if combination is None:
        msg = "Playing project", os.path.basename(project)
    else:
        msg = "Rendering project %s to: %s" % (os.path.basename(project), combination)

    print bcolors.OKBLUE + len(msg) * '='
    print msg
    print len(msg) * '=' + bcolors.ENDC

    dest_file = os.path.join(dest_dir, os.path.basename(project) +
                             '-' + combination.acodec +
                             combination.vcodec + '.' +
                             combination.container)
    profile = get_profile(combination)
    command = "ges-launch-1.0 -l %s -f %s -o %s " % (project, profile, dest_file)
    for path in paths:
        command += " -P %s" % path

    duration = timeout = getDuration(project)
    if combination:
        timeout *= 3  # Give us 2 time the length of the timeline to render
        print "Timeout set to %is" % timeout

    if elem is not None:
        elem.attrib["classname"] = str(comb).replace(' ', '_')
        elem.attrib["name"] = os.path.basename(project)

    start = time.time()
    stderr = open("sterr_o", 'wr')
    try:
        subprocess32.check_output(command, stderr=stderr, timeout=timeout, shell=True)
        asset = GES.UriClipAsset.request_sync(dest_file)
        if not asset:
            err = ET.SubElement(elem, 'failure')
            err.attrib["type"] = "Wrong rendered file"
            tmpf = open("sterr_o", 'r')
            err.text = "Rendered file could not be discovered\n %s" % tmpf.read()
            tmpf.close()
        elif asset.duration != duration:
            err = ET.SubElement(elem, 'failure')
            err.attrib["type"] = "Wrong rendered file"
            tmpf = open("sterr_o", 'r')
            err.text = "Rendered file as wrong duration (real: %s, expected %s)\n %s" \
                       % (print_ns(asset.duration()),
                          print_ns (duration),
                          tmpf.read())
            tmpf.close()
    except subprocess32.TimeoutExpired as e:
        msg = bcolors.FAIL, "TIMEOUT: running %s in %s:\n\n %s" % (command,
              os.getcwd(), e.output), bcolors.ENDC
        print msg
        if elem is not None:
            err = ET.SubElement(elem, 'failure')
            err.attrib["type"] = "Timeout"
            tmpf = open("sterr_o", 'r')
            err.text = tmpf.read()
            tmpf.close()
        ret = False
    except subprocess32.CalledProcessError as e:
        msg = "\n\n%sFAILED to run project:%s with profile: %s:\n%s%s" \
            % (bcolors.FAIL, project, profile, e.output, bcolors.ENDC)
        print msg
        if elem is not None:
            err = ET.SubElement(elem, 'failure')
            err.attrib["type"] = "Fail"
            tmpf = open("sterr_o", 'r')
            err.text = tmpf.read()
            tmpf.close()
        ret = False

    stderr.close()
    if elem is not None:
        elem.attrib["time"] = str(int(time.time() - start))

    return ret


if "__main__" == __name__:
    parser = OptionParser()
    parser.add_option("-o", "--output-path", dest="dest",
                      default="~/Videos/ges-rendered-projects",
                      help="Set the path to which projects should be renderd")
    parser.add_option("-p", "--asset-path", dest="paths",
                      default=[],
                      help="Paths in which to look for moved assets")
    (options, args) = parser.parse_args()

    options.dest = os.path.expanduser(os.path.abspath(options.dest))

    Gst.init(None)
    GES.init()

    print "Creating directory: %s" % options.dest
    try:
        os.makedirs(options.dest)
        print "Created directory: %s" % options.dest
    except OSError:
        pass

    projects = list()
    for proj in args:
        if Gst.uri_is_valid(proj):
            projects.append(proj)
        else:
            projects.append("file://" + proj)

    if isinstance(options.paths, str):
        options.paths = [options.paths]

    fails = 0
    root = ET.Element('testsuites')
    testsuite = ET.SubElement(root, 'testsuite')
    testsuite.attrib["tests"] = str(len(projects) * len(combinations))
    for proj in projects:
        for comb in combinations:
            elem = ET.SubElement(testsuite, 'testcase')
            if launch_project(proj, comb, options.dest, options.paths, elem) is False:
                fails += 1
    indent(root)
    tree = ET.ElementTree(root)
    tree.write('results.xml')
