import subprocess32
import os
from optparse import OptionParser
from buildgst import bcolors
from gi.repository import GES, Gst

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
                            formats[combination.acodec])

def getDuration(project):

    proj = GES.Project.new(project)
    tl = proj.extract()
    duration = tl.get_meta("duration")
    if duration is not None:
        return duration / Gst.SECOND
    return 10 * 60


def launch_project(project, combination, dest_dir):
    if combination is None:
        msg = "Playing project", os.path.basename (project)
    else:
        msg = "Rendering project %s to: %s" % (os.path.basename (project), combination)

    print bcolors.OKBLUE + len(msg) * '='
    print msg
    print len(msg) * '=' + bcolors.ENDC

    dest_file = os.path.join(dest_dir, os.path.basename(project) +
                             '-' + combination.acodec +
                             combination.vcodec + '.' +
                             combination.container)
    profile = get_profile(combination)
    command = "ges-launch-1.0 -l %s -f %s -o %s 1>&2" % (project, profile, dest_file)
    timeout = getDuration(project)
    if combination:
        timeout *= 3 # Give us 2 time the length of the timeline to render
        print "Timeout set to %is" % timeout

    try:
        subprocess32.check_output(command, timeout=timeout, shell=True)
    except subprocess32.TimeoutExpired as e:
        print bcolors.FAIL, "TIMEOUT: running %s in %s:\n\n %s" % (command,
              os.getcwd(), e.output), bcolors.ENDC
    except subprocess32.CalledProcessError as e:
        print"\n\n%sFAILED to run project:%s with profile: %s:\n%s%s" \
            % (bcolors.FAIL, project, profile, e.output, bcolors.ENDC)
        raise e


if "__main__" == __name__:
    parser = OptionParser()
    parser.add_option("-o", "--output-path", dest="dest",
                      default="~/Videos/ges-rendered-projects",
                      help="Set the path to which projects should be renderd")
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

    for proj in args:
        for comb in combinations:
            launch_project(proj, comb, options.dest)
