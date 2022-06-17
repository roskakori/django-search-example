#!/bin/sh
set -ex
poetry update
pre-commit autoupdate
