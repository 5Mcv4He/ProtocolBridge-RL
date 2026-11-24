#!/bin/bash
# Root-owned launcher; invoked by the trusted host controller on UTM Linux.
# A new mount/PID namespace prevents exposing host processes through /proc.
set -euo pipefail
root=${PB_RUNTIME_ROOT:-/opt/protocolbridge-runtime}
uid=${PB_SOLVER_UID:-1101}
gid=${PB_SOLVER_GID:-1000}
work=${1:?solver work path inside sandbox}
[[ "$work" =~ ^/work/[a-zA-Z0-9_-]+$ ]] || exit 2
exec unshare --mount --pid --ipc --fork /bin/bash -c '
 set -e
 mount --make-rprivate /
 mount -t proc -o nosuid,nodev,noexec proc "$1/proc"
 cd "$1"
 ulimit -c 0
 ulimit -n 1024
 exec /usr/bin/setpriv --no-new-privs /usr/sbin/chroot --userspec="$2:$3" "$1" /usr/bin/env -i PATH=/opt/dsh/bin:/usr/bin:/bin HOME="$4" LANG=C.UTF-8 /opt/dsh/bin/python /opt/pb/utm_worker.py "$4"
' sandbox "$root" "$uid" "$gid" "$work"
