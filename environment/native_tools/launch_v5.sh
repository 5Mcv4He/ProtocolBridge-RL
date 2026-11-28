#!/bin/bash
# Separate version: a per-process ephemeral work/tmp tree, immutable installed runtime.
set -euo pipefail
root=/opt/protocolbridge-runtime
uid=1101
gid=1000
work=${1:?solver work path}
[[ "$work" =~ ^/work/[a-zA-Z0-9_-]+$ ]] || exit 2
exec unshare --mount --pid --ipc --fork /bin/bash -c '
 set -e
 mount --make-rprivate /
 mount -t proc -o nosuid,nodev,noexec proc "$1/proc"
 mount -t tmpfs -o nosuid,nodev,size=256m,mode=755 tmpfs "$1/work"
 mount -t tmpfs -o nosuid,nodev,size=64m,mode=1777 tmpfs "$1/tmp"
 mkdir "$1$4"
 chown "$2:$3" "$1$4"
 chmod 700 "$1$4"
 cd "$1"
 ulimit -c 0
 ulimit -n 256
 exec /usr/bin/setpriv --no-new-privs /usr/sbin/chroot --userspec="$2:$3" "$1" /usr/bin/env -i PATH=/opt/dsh/bin:/usr/bin:/bin HOME="$4" LANG=C.UTF-8 /opt/dsh/bin/python /opt/pb/native-tools-v5/worker_v5.py "$4"
' sandbox "$root" "$uid" "$gid" "$work"
