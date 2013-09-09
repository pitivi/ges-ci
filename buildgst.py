#!/bin/python
# Indentation = 4 spaces.
#
# This script sets up the environment to use and develop Pitivi.
#
# LD_LIBRARY_PATH, DYLD_LIBRARY_PATH, PKG_CONFIG_PATH are set to
# prefer the cloned git projects and to also allow using the installed ones.
import os
import subprocess
import platform
import multiprocessing
from os.path import join
from optparse import OptionParser


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


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

GST_ENV_PATH = env("GST_ENV_PATH") if env("GST_ENV_PATH") else join(env("HOME"), "gst-git")
BASE_PREFIX = join(GST_ENV_PATH, "prefix")
GST_MIN_VERSION = "1.1.1.4"
GLIB_MIN_VERSION = "2.34.3"


class Recipe:
    recipes = None

    def __init__(self,
                 module,
                 nick='',
                 branch="master",
                 autogen='./autogen.sh',
                 make="make -j%i" % multiprocessing.cpu_count(),
                 autogen_param='--disable-gtk-doc',
                 force_autogen=False,
                 install="",
                 gitrepo="git://anongit.freedesktop.org/gstreamer/%s",
                 extra_remotes=[],
                 check='',
                 check_integration='',
                 force_build=False,
                 ldpaths=[],
                 gst_plugin_paths=[]):
        self.module = module
        self.nick = nick
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
        self.ldpaths = ldpaths
        self.gst_plugin_paths = gst_plugin_paths
        self.extra_remotes = extra_remotes

RECIPES = [
    Recipe("glib",
           branch="2.34.2",
           autogen_param="--prefix=%s" % BASE_PREFIX,
           install="make install",
           gitrepo="git://git.gnome.org/%s"),

    Recipe("gstreamer",
           autogen_param="--disable-docbook",
           ldpaths=[("%s/libs/gst/%s/.libs", "base net check controller"),
           ("%s/%s/.libs", "gst")],
           gst_plugin_paths=[("%s/%s", "ext gst plugins")]),

    Recipe("gst-plugins-base", nick='base',
           ldpaths=[("%s/gst-libs/gst/%s/.libs",
                  "app audio cdda fft interfaces pbutils netbuffer riff rtp rtsp sdp tag utils video")],
           gst_plugin_paths=[("%s/%s", "ext gst sys")]),

    Recipe("gst-plugins-good", nick='good',
           gst_plugin_paths=[("%s/%s", "ext gst sys")]),

    Recipe("gst-plugins-ugly", nick='ugly',
           gst_plugin_paths=[("%s/%s", "ext gst sys")]),

    Recipe("gst-plugins-bad", nick='bad',
           ldpaths=[("%s/gst-libs/gst/%s/.libs", "basecamerabinsrc codecparsers interfaces")],
           gst_plugin_paths=[("%s/%s", "ext gst sys")]),

    Recipe("gnonlin", nick='gnl',
           gst_plugin_paths=[("%s/%s", "gnl")]),

    Recipe("gst-ffmpeg", nick='libav',
           ldpaths=[("%s/gst-libs/ext/ffmpeg/%s", "libavformat libavutil libavcodec libpostproc libavdevice")],
           gst_plugin_paths=[("%s/%s", "ext")]),

    Recipe("gst-editing-services",
           check="make check", nick='ges',
           check_integration="""cd tests/check && \
                                CK_TIMEOUT_MULTIPLIER=10 GST_DEBUG_FILE=test.log \
                                GES_MUTE_TESTS=yes make check-integration 2>&1 \
                                |grep 'running test\|integration.c\|Checks.*Failures' 1>&2""")]


def find_recipe(name):
    for r in RECIPES:
        if r.module == name or r.nick == name:
            return r

    return None


def check_needed_repos():
    #
    # Everything below this line shouldn't be edited!
    #
    try:
        subprocess.check_output("pkg-config glib-2.0 --atleast-version=%s" % GLIB_MIN_VERSION, shell=True)
    except subprocess.CalledProcessError:
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


def set_env_variables():
    # set up a bunch of ldpaths
    setenv('PATH',
           join(GST_ENV_PATH, "gst-editing-services", "tools"),
           join(GST_ENV_PATH, "pitivi", "bin"),
           join(GST_ENV_PATH, "gstreamer", "tools"),
           join(GST_ENV_PATH, "gst-plugins-base", "tools"),
           join(BASE_PREFIX, 'bin'))

    # /some/path: makes the dynamic linker look in . too, so avoid this
    setenv('LD_LIBRARY_PATH', join(BASE_PREFIX, 'lib'))
    setenv('DYLD_LIBRARY_PATH', join(BASE_PREFIX, 'lib'))
    setenv('GI_TYPELIB_PATH', join(BASE_PREFIX, 'share', 'gir-1.0'))
    setenv('PKG_CONFIG_PATH', join(BASE_PREFIX, 'lib', 'pkgconfig'), join(GST_ENV_PATH, 'pygobject'))

    #if pkg-config --exists --print-errors 'gstreamer-1.0 >= 1.1.0.1'; the#n
    try:
        subprocess.check_output("pkg-config --exists --print-errors 'gstreamer-1.0 >= 1.1.0.1'", shell=True)
        print "Using system-wide GStreamer 1.0"
    except:
        print"Using a local build of GStreamer 1.0"
        for recipe in RECIPES:
            for itpath, vals in recipe.ldpaths:
                for subdir in vals.split(' '):
                    setenv('LD_LIBRARY_PATH', join(GST_ENV_PATH, itpath) % (recipe.module, subdir))
                    setenv('DYLD_LIBRARY_PATH', join(GST_ENV_PATH, itpath) % (recipe.module, subdir))
                    setenv('PKG_CONFIG_PATH', join(GST_ENV_PATH, "%s/pkgconfig" % recipe.module))
                    if ".libs" in itpath:
                        setenv('GI_TYPELIB_PATH', join(GST_ENV_PATH, itpath.replace(".libs", ""))
                               % (recipe.module, subdir))

            for form, vals in recipe.gst_plugin_paths:
                for subdir in vals.split(' '):
                    setenv("GST_PLUGIN_PATH", join(GST_ENV_PATH, form) % (recipe.module, subdir))

        os.environ['GST_PLUGIN_SYSTEM_PATH'] = ''
        # set our registry somewhere else so we don't mess up the registry generated
        # by an installed copy
        os.environ['GST_REGISTRY'] = join(GST_ENV_PATH, "gstreamer/registry.dat")
        # Point at the uninstalled plugin scanner
        os.environ['GST_PLUGIN_SCANNER'] = join(GST_ENV_PATH, "gstreamer/libs/gst/helpers/gst-plugin-scanner")

        # once MANPATH is set, it needs at least an "empty"component to keep pulling
        # in the system-configured man ldpaths from man.config
        # this still doesn't make it work for the uninstalled case, since man goes
        # look for a man directory "nearby" instead of the directory I'm telling it to
        setenv("MANPATH", join(GST_ENV_PATH, "gstreamer/tools"), join(BASE_PREFIX, "share/man"))


def print_recipes(message):
    print message
    for recipe in RECIPES:
        if recipe.build is False and recipe.force_build is False:
            continue
        print "    %s at: %s" % (recipe.module, recipe.branch)


def run_command(command, recipe, verbose_level=None, is_fatal=True):
    if verbose_level is None:
        command += " 2>&1"
    elif verbose_level > 2:
        command += " 1>&2"

    print '  Running %s... ' % command
    try:
        stdout = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError, e:
        print "ERROR: running %s in %s:\n\n %s" % (command,
                                                   os.getcwd(),
                                                   e.output)
        if is_fatal:
            print_recipes("\n\n%sFAILED to build:%s%s" % (bcolors.FAIL, recipe.module, bcolors.ENDC))
            raise e
        else:
            return e
    if verbose_level == 2:
        print stdout
    print 90 * ' ' + bcolors.OKGREEN + "OK" + bcolors.ENDC
    return None


def set_hashes():
    linestring = open('Changes', 'r').read()

    for line in linestring.split('\n'):
        line = line.replace(" ", '')
        try:
            module = line.split(":")[0]
            hash = line.split(":")[1]
        except IndexError:
            continue

        recipe = find_recipe(module)
        if recipe is not None:
            recipe.branch = hash


def init(build=False):
    if build:
        check_needed_repos()
    set_env_variables()


def checkout(recipe):
    os.chdir(GST_ENV_PATH)
    try:
        os.chdir(join(GST_ENV_PATH, recipe.module))
    except OSError:
        run_command('git clone  ' + recipe.gitrepo, recipe)
        os.chdir(join(GST_ENV_PATH, recipe.module))

    if recipe.extra_remotes:
        for name, remote in recipe.extra_remotes:
            run_command('git remote add %s %s' % (name, remote), recipe)
            run_command('git fetch %s' % (name), recipe)


def build(module, verbose_level=None, force_autogen=False):

    recipe = find_recipe(module)
    if recipe is None:
        raise KeyError("%s not found" % module)

    print "\nBuidling %s" % recipe.module
    os.chdir(join(GST_ENV_PATH, recipe.module))
    run_command('git checkout -qf %s' % recipe.branch, recipe, verbose_level=verbose_level)
    if force_autogen is True or not \
            os.path.isfile(join(os.getcwd(), "configure"))  \
            or recipe.force_autogen is True:
        run_command(recipe.autogen, recipe, verbose_level=verbose_level)
    run_command(recipe.make, recipe, verbose_level=verbose_level)
    if recipe.install:
        run_command(recipe.install, recipe, verbose_level=verbose_level)
    if recipe.check:
        run_command(recipe.check, recipe, verbose_level=verbose_level)
    if recipe.check_integration:
        lev = 1 if verbose_level < 1 else verbose_level
        if run_command(recipe.check_integration,
                       recipe,
                       verbose_level=lev,
                       is_fatal=False) is not True:
            print "\n\n%s=================================" % bcolors.WARNING
            print "Errors during integration tests"
            print "=================================%s\n" % bcolors.ENDC


def install_deps(verbosity=None):
    distro = platform.linux_distribution()
    print "Distribution: ", str(distro)
    if distro[0] == 'Ubuntu' and distro[1] >= 12.04:
        run_command("sudo echo 'yes' | sudo add-apt-repository ppa:gstreamer-developers/ppa", verbosity)
        run_command("sudo apt-get update", verbosity)
        run_command("sudo apt-get install build-essential automake libtool itstool gtk-doc-tools gnome-common gnome-doc-utils yasm flex bison", verbosity)
        run_command("sudo apt-get build-dep gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly", verbosity)
    else:
        print "Could not install dependencies"

if "__main__" == __name__:
    parser = OptionParser()
    parser.add_option("-f", "--force-autogen", dest="force_autogen",
                      action="store_true", default=False,
                      help="Set to force autogen")
    parser.add_option("-u", "--use-hashes", dest="use_hashes",
                      action="store_true", default=False,
                      help="Set to force autogen")
    parser.add_option("-v", "--verbose", dest="verbose",
                      default=None, help="Set verbosity")
    parser.add_option("-d", "--install-depencies", dest="install_deps",
                      action="store_true", default=False,
                      help="Try to automatically install dependencies")
    (options, args) = parser.parse_args()

    # mkdirs if needed
    print bcolors.OKBLUE + len("Base path is: %s" % os.getcwd()) * '='
    print "Base path is: %s" % os.getcwd()
    print len("Base path is: %s\n\n" % os.getcwd()) * '=' + bcolors.ENDC

    init(True)

    if options.install_deps:
        install_deps()
    if options.use_hashes:
        set_hashes()

    try:
        os.makedirs(GST_ENV_PATH)
        print "Created directory: %s" % GST_ENV_PATH
    except OSError:
        pass

    os.chdir(GST_ENV_PATH)
    for recipe in RECIPES:
        if recipe.build is False and recipe.force_build is False:
            continue
        try:
            checkout(recipe)
        except subprocess.CalledProcessError, e:
            exit(1)

    for recipe in RECIPES:
        if recipe.build is False and recipe.force_build is False:
            continue

        try:
            build(recipe.module, options.verbose, options.force_autogen)
        except subprocess.CalledProcessError, e:
            exit(1)

    print_recipes("\n\n%sSuccessfully built:%s" % (bcolors.OKGREEN, bcolors.ENDC))
