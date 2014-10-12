#!/bin/sh -xue

VERSION=1.2
DIST=pyweek-lightswitch-$VERSION

rm -rf $DIST || true
mkdir $DIST
cp -r *.ttf run_game.py picture_render.py README.md pictures_vbuf.zip sounds $DIST
COPYFILE_DISABLE=1 zip -r $DIST.zip $DIST
