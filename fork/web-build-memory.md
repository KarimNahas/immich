# More memory for the web build

## What changes

The image build gives Node 4 GB of heap while building the web app.

## Why

The web build ran out of memory when the image was built under Docker Desktop with its default
memory limit.

## How

- `server/Dockerfile`: `ENV NODE_OPTIONS="--max-old-space-size=4096"` in the web build stage.

## Test

None. Building the image is the test.

## Drop this when

The image builds without it, for example after raising Docker's memory limit.
