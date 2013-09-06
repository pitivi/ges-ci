#!/bin/python
# Indentation = 4 spaces.
#
# This script sets up the environment to use and develop Pitivi.
#
# LD_LIBRARY_PATH, DYLD_LIBRARY_PATH, PKG_CONFIG_PATH are set to
# prefer the cloned git projects and to also allow using the installed ones.
import os
import subprocess
from os.path import join
from optparse import OptionParser


def env(name):
    try:
        ret = os.getenv(name)
        if ret is None:
            return ""
        return ret
    except:
        return ''


def setenv(var, *args):
    val = env(var)
    for v in args:
        if val:
            val += ':'
        val += v
    os.environ[var] = val

# If you care about building the GStreamer/GES developer API documentation:
BUILD_DOCS = False

BASE_PATH = env("BASE_PATH") if env("BASE_PATH") else join(env("HOME"), "gst-git")
BASE_PREFIX = join(BASE_PATH, "prefix")
GST_MIN_VERSION = "1.1.1.4"
GLIB_MIN_VERSION = "2.34.3"


class Recipe:
    def __init__(self,
                 module,
                 branch="master",
                 autogen='./autogen.sh',
                 make="make",
                 autogen_param='--disable-gtk-doc',
                 force_autogen=False,
                 install="",
                 gitrepo="git://anongit.freedesktop.org/gstreamer/%s",
                 check='',
                 check_integration='',
                 force_build=False):
        self.module = module
        self.gitrepo = gitrepo % module
        self.branch = branch
        self.autogen = autogen + " " + autogen_param + " "
        self.make = make
        self.install = install
        self.check = check
        self.check_integration = check_integration
        self.build = False
        self.force_build = force_build
        self.force_autogen = force_autogen


RECIPES = [
    Recipe("glib",
           branch="2.34.2",
           autogen_param="--prefix=%s" % BASE_PREFIX,
           install="make install",
           gitrepo="git://git.gnome.org/%s"),

    Recipe("gstreamer",
           autogen_param="--disable-docbook"),

    Recipe("gst-plugins-base"),

    Recipe("gst-plugins-good"),

    Recipe("gst-plugins-ugly"),

    Recipe("gst-plugins-bad"),

    Recipe("gnonlin"),

    Recipe("gst-ffmpeg"),

    Recipe("gst-editing-services",
           check="make check",
           check_integration="cd tests/check && GES_MUTE_TESTS=yes make check-integration"),
]


def find_recipe(name):
    for r in RECIPES:
        if r.module == name:
            return r

    return None

#
# Everything below this line shouldn't be edited!
#
try:
    subprocess.check_output("pkg-config glib-2.0 --atleast-version=%s" % GLIB_MIN_VERSION, shell=True)
    print "glib is up to date, using the version already available."
except subprocess.CalledProcessError:
    print "Building GLib"
    find_recipe("glib").build = True

try:
    print subprocess.check_output("pkg-config --exists --print-errors 'gstreamer-1.0 >= %s'"
                                  % GST_MIN_VERSION,
                                  shell=True)
except subprocess.CalledProcessError:
    find_recipe("gstreamer").build = True
    find_recipe("gst-plugins-base").build = True
    find_recipe("gst-plugins-good").build = True
    find_recipe("gst-plugins-ugly").build = True
    find_recipe("gst-plugins-bad").build = True
    find_recipe("gst-ffmpeg").build = True


# The following decision has to be made before we've set any env variables,
# otherwise the script will detect our "gst uninstalled" and think it's the
# system-wide install.
find_recipe("gnonlin").build = True
find_recipe("gst-editing-services").build = True

# set up a bunch of paths
setenv('PATH',
       join(BASE_PATH, "gst-editing-services", "tools"),
       join(BASE_PATH, "pitivi", "bin"),
       join(BASE_PATH, "gstreamer", "tools"),
       join(BASE_PATH, "gst-plugins-base", "tools"),
       join(BASE_PREFIX, 'bin'))


# /some/path: makes the dynamic linker look in . too, so avoid this
setenv('LD_LIBRARY_PATH', join(BASE_PREFIX, 'lib'))
setenv('DYLD_LIBRARY_PATH', join(BASE_PREFIX, 'lib'))
setenv('GI_TYPELIB_PATH', join(BASE_PREFIX, 'share', 'gir-1.0'))
setenv('PKG_CONFIG_PATH', join(BASE_PREFIX, 'lib', 'pkgconfig'), join(BASE_PATH, 'pygobject'))

#if pkg-config --exists --print-errors 'gstreamer-1.0 >= 1.1.0.1'; the#n
try:
    subprocess.check_output("pkg-config --exists --print-errors 'gstreamer-1.0 >= 1.1.0.1'", shell=True)
    print "Using system-wide GStreamer 1.0"
except:
    print"Using a local build of GStreamer 1.0"
    paths = {"gst-ffmpeg/gst-libs/ext/ffmpeg/%s": "libavformat libavutil libavcodec libpostproc libavdevice",
             "gst-plugins-base/gst-libs/gst/%s/.libs": "app audio cdda fft interfaces pbutils netbuffer riff rtp rtsp sdp tag utils video",
             "gst-plugins-bad/gst-libs/gst/%s/.libs": "basecamerabinsrc codecparsers interfaces",
             "gstreamer/libs/gst/%s/.libs": "base net check controller",
             "gstreamer/%s/.libs": "gst"}
    # GStreamer ffmpeg libraries
    for itpath, vals in paths.iteritems():
        for subdir in vals.split(' '):
            setenv('LD_LIBRARY_PATH', join(BASE_PATH, itpath) % subdir)
            setenv('DYLD_LIBRARY_PATH', join(BASE_PATH, itpath) % subdir)
            if ".libs" in itpath:
                setenv('GI_TYPELIB_PATH', join(BASE_PATH, itpath.replace(".libs", "")) % subdir)

    ## GStreamer plugins base libraries
    for path in "app audio cdda fft interfaces pbutils netbuffer riff rtp rtsp sdp tag utils video".split(" "):
        setenv('LD_LIBRARY_PATH', join(BASE_PATH, "gst-plugins-base/gst-libs/gst/", path, ".libs"))

    setenv('PKG_CONFIG_PATH',
           join(BASE_PATH, "gstreamer/pkgconfig"),
           join(BASE_PATH, "gst-plugins-base/pkgconfig"),
           join(BASE_PATH, "gst-plugins-good/pkgconfig"),
           join(BASE_PATH, "gst-plugins-ugly/pkgconfig"),
           join(BASE_PATH, "gst-plugins-bad/pkgconfig"),
           join(BASE_PATH, "gst-ffmpeg/pkgconfig"),
           join(BASE_PATH, "gst-editing-services/pkgconfig"))

    setenv("GST_PLUGIN_PATH", join(BASE_PATH, "gstreamer/plugins"),
           join(BASE_PATH, "gst-plugins-base/ext"),
           join(BASE_PATH, "gst-plugins-base/gst"),
           join(BASE_PATH, "gst-plugins-base/sys"),
           join(BASE_PATH, "gst-plugins-good/ext"),
           join(BASE_PATH, "gst-plugins-good/gst"),
           join(BASE_PATH, "gst-plugins-good/sys"),
           join(BASE_PATH, "gst-plugins-ugly/ext"),
           join(BASE_PATH, "gst-plugins-ugly/gst"),
           join(BASE_PATH, "gst-plugins-ugly/sys"),
           join(BASE_PATH, "gst-plugins-bad/ext"),
           join(BASE_PATH, "gst-plugins-bad/gst"),
           join(BASE_PATH, "gst-plugins-bad/sys"),
           join(BASE_PATH, "gst-ffmpeg/ext/"),
           join(BASE_PATH, "gnonlin/gnl/"),
           join(BASE_PATH, "gst-openmax/omx/.libs"),
           join(BASE_PATH, "gst-omx/omx/.libs"),
           join(BASE_PATH, "gst-plugins-gl/gst/.libs"),
           join(BASE_PATH, "clutter-gst/clutter-gst/.libs"),
           join(BASE_PATH, "plugins"),
           join(BASE_PATH, "farsight2/gst"),
           join(BASE_PATH, "farsight2/transmitters"),
           join(BASE_PATH, "libnice/gst"))


def run_command(command):
    info = '  Running %s... ' % command
    print info
    try:
        subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError, e:
        print "ERROR: running %s in %s:\n\n %s" % (command,
                                                   os.getcwd(),
                                                   e.output)
        exit(1)
    print 70 * ' ' + "OK"
# mkdirs if needed
try:
    os.makedirs(BASE_PATH)
    print "Creating %s" % BASE_PATH
except OSError:
    pass

os.chdir(BASE_PATH)
print "\n===================================="
print "  Base path is: %s" % os.getcwd()
print "====================================\n"

parser = OptionParser()
parser.add_option("-f", "--force-autogen", dest="force_autogen",
                  action="store_true", default=False,
                  help="Set to force autogen")
(options, args) = parser.parse_args()

for recipe in RECIPES:
    if recipe.build is False and recipe.force_build is False:
        continue

    print "\nBuidling %s" % recipe.module
    os.chdir(BASE_PATH)
    try:
        os.chdir(join(BASE_PATH, recipe.module))
    except OSError:
        run_command('git clone  ' + recipe.gitrepo)
        os.chdir(join(BASE_PATH, recipe.module))

    run_command('git checkout %s' % recipe.branch)
    if options.force_autogen is True or not \
            os.path.isfile(join(os.getcwd(), "configure"))  \
            or recipe.force_autogen is True:
        run_command(recipe.autogen)
    run_command(recipe.make)
    if recipe.install:
        run_command(recipe.install)
    if recipe.check:
        run_command(recipe.check)
    if recipe.check_integration:
        run_command(recipe.check_integration)
    print "\nBuidling %s" % recipe.module
