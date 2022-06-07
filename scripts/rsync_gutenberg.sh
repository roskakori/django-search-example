#!/bin/sh
MIRROR=aleph.gutenberg.org
rsync --include "*/" --include "*.htm" --include "*.txt" --exclude "*"  -av --del ${MIRROR}::gutenberg gutenberg
