import signal
import subprocess32
import time
import os
from optparse import OptionParser
from buildgst import bcolors
from gi.repository import GES, Gst, GLib
import xml.etree.ElementTree as ET

DURATION_TOLERANCE = Gst.SECOND / 2

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
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
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


def getDuration(project_uri):

    proj = GES.Project.new(project_uri)
    tl = proj.extract()
    if tl is None:
        duration = None
    else:
        duration = tl.get_meta("duration")
    if duration is not None:
        return duration / Gst.SECOND
    return 10 * 60


def launch_project(project_uri, combination, dest_uri, paths=[], elem=None):
    ret = True

    if not Gst.uri_is_valid(dest_uri):
        dest_uri = GLib.filename_to_uri(dest_uri, None)

    if combination is None:
        msg = "Playing project", os.path.basename(project_uri)
    else:
        msg = "Rendering project %s to: %s" % (os.path.basename(project_uri), combination)

    print bcolors.OKBLUE + len(msg) * '='
    print msg
    print len(msg) * '=' + bcolors.ENDC

    dest_file = os.path.join(dest_uri, os.path.basename(project_uri) +
                             '-' + combination.acodec +
                             combination.vcodec + '.' +
                             combination.container)
    profile = get_profile(combination)
    command = "ges-launch-1.0 -l %s -f %s -o %s " % (project_uri, profile, dest_file)
    for path in paths:
        command += " -P %s" % path

    duration =  getDuration(project_uri)
    if elem is not None:
        elem.attrib["classname"] = str(comb).replace(' ', '_')
        elem.attrib["name"] = os.path.basename(project_uri)

    timeout = False
    last_size = 0
    last_change_ts = time.time()
    start = time.time()
    fstderr = open("sterr_o", 'wr')
    print "Launching: %s" % command
    process = subprocess32.Popen(command, stderr=fstderr,
                                 stdout=subprocess32.PIPE,
                                 shell=True,
                                 preexec_fn=os.setsid)
    stdo, stde = None, None
    while True:
        try:
            stdo, stde = process.communicate(timeout=1)
        except subprocess32.TimeoutExpired:
            pass

        if process.returncode is not None:
            break

        sz = os.stat(GLib.filename_from_uri(dest_file)[0]).st_size
        if sz == last_size:
            if time.time() - last_change_ts > 10:
                print "10 seconds without any change in rendered file => timeout"
                timeout = True
                os.killpg(process.pid, signal.SIGTERM)
                break
        else:
            last_change_ts = time.time()
            last_size = sz

        if stdo:
            print stdo

    tmpf = open("sterr_o", 'r')
    if process.returncode == 0:
        try:
            asset = GES.UriClipAsset.request_sync(dest_file)
            if duration - DURATION_TOLERANCE <= asset.get_duration() <= duration + DURATION_TOLERANCE:
                err = ET.SubElement(elem, 'failure')
                err.attrib["type"] = "Wrong rendered file"
                err.text = "Rendered file as wrong duration (real: %s, expected %s)\n %s" \
                           % (print_ns(asset.get_duration()),
                              print_ns(duration),
                              tmpf.read().replace(">", '_').replace('<', '_'))
        except Exception as e:
            err = ET.SubElement(elem, 'failure')
            err.attrib["type"] = "Wrong rendered file"
            tmpf.close()
    else:
        stderr = tmpf.read()
        if timeout is True:
            missing_eos = False
            try:
                asset = GES.UriClipAsset.request_sync(dest_file)
                if asset.get_duration() == duration:
                    missing_eos = True
            except:
                pass
            print bcolors.FAIL, "TIMEOUT: running %s in %s:\n\n %s" % (command,
                  os.getcwd(), stderr), bcolors.ENDC

            if elem is not None:
                err = ET.SubElement(elem, 'failure')
                err.attrib["type"] = "Timeout"
                if missing_eos is True:
                    err.text = "The rendered file add right duration, MISSING EOS?\n\n" + \
                            stderr
                else:
                    err.text = stderr
            ret = False
        else:
            print "\n\n%sFAILED to run project:%s with profile: %s:\n%s%s" \
                % (bcolors.FAIL, project_uri, profile, stderr, bcolors.ENDC)
            if elem is not None:
                err = ET.SubElement(elem, 'failure')
                err.attrib["type"] = "Fail"
                err.text = stderr
            ret = False

    tmpf.close()
    fstderr.close()
    if elem is not None:
        elem.attrib["time"] = str(int(time.time() - start))
    print "%sDone seconds: %d %s" %(bcolors.OKGREEN,
                                       int(time.time() - start),
                                       bcolors.ENDC)

    return ret


if "__main__" == __name__:
    parser = OptionParser()
    default_opath = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)
    if default_opath:
        default_opath = os.path.join(default_opath, "ges-rendered-projects")
    else:
        default_opath = os.path.join(os.path.expanduser('~'), "Video",
                "ges-rendered-projects")
    parser.add_option("-o", "--output-path", dest="dest",
                      default=default_opath,
                      help="Set the path to which projects should be renderd")
    parser.add_option("-p", "--asset-path", dest="paths",
                      default=[],
                      help="Paths in which to look for moved assets")
    (options, args) = parser.parse_args()

    Gst.init(None)
    GES.init()

    if not Gst.uri_is_valid(options.dest):
        options.dest = GLib.filename_to_uri(options.dest, None)

    print "Creating directory: %s" % options.dest
    try:
        os.makedirs(GLib.filename_from_uri(options.dest)[0])
        print "Created directory: %s" % options.dest
    except OSError:
        pass

    projects = list()
    for proj in args:
        if Gst.uri_is_valid(proj):
            projects.append(proj)
        else:
            projects.append(GLib.filename_to_uri(proj, None))

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
