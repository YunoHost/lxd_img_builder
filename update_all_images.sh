#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

REPO="$1"

status=0

update_image() {
    properties=("$@")
    if ! "$SCRIPT_DIR/image_builder.py" -o "$REPO" "${properties[@]}" &> "$SCRIPT_DIR/build_bullseye_stable_$variant.log"; then
        echo "Could not build image ${properties[*]}!"
        status=1
    fi
}

for variant in build-and-lint before-install all; do
    # Bullseye
    update_image bullseye stable "$variant"
    update_image bullseye unstable "$variant"
    update_image bullseye testing "$variant"

    # Bookworm only supports unstable, testing
    # update_image bookworm stable "$variant"
    update_image bookworm unstable "$variant"
    update_image bookworm testing "$variant"
done

# Then remove old images. It might disturb downloads in progress though...
"$SCRIPT_DIR/prune_incus_simplestreams.py" -r "$REPO"

exit "$status"
