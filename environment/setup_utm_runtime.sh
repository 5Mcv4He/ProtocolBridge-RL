#!/usr/bin/env bash
# Run on the licensed UTM Linux host. Installs only into a dedicated new rootfs.
# Obtain the Ubuntu Base archive and verify its published SHA256 before invocation.
set -euo pipefail
archive=${1:?Usage: setup_utm_runtime.sh VERIFIED_UBUNTU_BASE_AMD64_TAR_GZ}
root=/opt/protocolbridge-runtime
script_dir=$(cd "$(dirname "$0")" && pwd)
if test -e "$root" && ! test -f "$root/.protocolbridge-managed"; then
  echo 'Existing unmanaged runtime directory; inspect it before proceeding.' >&2
  exit 1
fi
if ! test -d "$root"; then
  sudo -n mkdir "$root"
  sudo -n tar -xzf "$archive" -C "$root"
  sudo -n touch "$root/.protocolbridge-managed"
fi
sudo -n cp /etc/resolv.conf "$root/etc/resolv.conf"
sudo -n mkdir -p "$root/proc" "$root/dev" "$root/work" "$root/opt/pb"
sudo -n unshare --mount --fork /bin/bash -c '
 set -e
 mount --make-rprivate /
 mount -t proc proc "$1/proc"
 mount --bind /dev "$1/dev"
 chroot "$1" /usr/bin/env DEBIAN_FRONTEND=noninteractive /bin/bash -ec "apt-get update -qq; apt-get install -y --no-install-recommends python3 python3-venv ca-certificates; if ! test -d /opt/dsh; then python3 -m venv /opt/dsh; fi"
 chroot "$1" /opt/dsh/bin/pip install --no-cache-dir deepseek-harness-sdk==0.2.2rc2
 chroot "$1" apt-get clean
' setup "$root"
if ! id pbsolver >/dev/null 2>&1; then
 sudo -n useradd -u 1101 -g 1000 -M -s /sbin/nologin pbsolver
fi
test "$(id -u pbsolver)" = 1101
sudo -n install -m 644 "$script_dir/utm_worker.py" "$root/opt/pb/utm_worker.py"
sudo -n install -m 755 "$script_dir/utm_sandbox.sh" /usr/local/sbin/pb-sandbox
sudo -n find "$root" -xdev -type f -perm /6000 -exec chmod a-s {} +
for spec in 'null 1 3' 'zero 1 5' 'random 1 8' 'urandom 1 9'; do
 read -r name major minor <<< "$spec"
 if ! test -e "$root/dev/$name"; then sudo -n mknod -m 666 "$root/dev/$name" c "$major" "$minor"; fi
done
sudo -n install -d -o 1101 -g 1000 -m 770 "$root/work/isolation-probe"
printf '{"probe_only":true}\n' | sudo -n /usr/local/sbin/pb-sandbox /work/isolation-probe
