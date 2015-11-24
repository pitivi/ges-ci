#!/bin/sh

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

BUILDDIR=$DIR
cd $BUILDDIR

xdg-app-builder $BUILDDIR/app $DIR/pitivi.json
xdg-app build $BUILDDIR/app bash -c "mv /app/share/applications/pitivi.desktop /app/share/applications/org.pitivi.Pitivi.desktop"
xdg-app build $BUILDDIR/app bash -c "cp pitivi_app /app/bin/pitivi_app"
xdg-app build-finish --verbose --command=pitivi_app --socket=x11 --socket=session-bus --talk-name=ca.desrt.dconf --filesystem=home $BUILDDIR/app/
