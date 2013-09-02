MODULES="gstreamer gst-plugins-base gst-plugins-good gst-plugins-ugly gst-plugins-bad gst-ffmpeg gnonlin gst-editing-services gst-python"

DIR=~/devel/pitivi/1.0-uninstalled/
cdir=$(pwd)
changed=
message="Changes in: "
for m in $MODULES
do
  cd $DIR/$m
  echo "Checking "$m
  has_changes=$(git fetch origin 2>&1)
  if [[ -n "$has_changes" ]]; then
    changed="$changed$(echo -e "\n\n====== $m =============\n\n ")"
    changed="$changed$(git log ..origin/master 2>&1)"
    changed="$changed$(echo -e "\n\n ")"
    message="$message $m"
  fi
  has_changes=
done

if [[ -z "$changed" ]]; then
  echo -e "No changes... Return"
  exit 0
fi

message="$message$(echo -e "\n \n ")"
for m in $MODULES
do
  cd $DIR/$m
  message="$message$m$(echo -e " $(git log --pretty=format:"%H %ad %an %ar %s" origin/master^..origin/master 2>&1) \n ")"
done

cd $cdir
echo "$changed" > Changes
message="$message$(echo -e "\n \n ")$changed"
git add Changes
git commit -m "$message"
git push origin master
