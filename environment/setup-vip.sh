#!/usr/bin/env bash
# Execute on the licensed EDA host, with DESIGNWARE_HOME already configured.
set -euo pipefail
: "${DESIGNWARE_HOME:?Set the installed AMBA SVT root}"
: "${1:?Usage: setup-vip.sh NEW_GENERATED_DIRECTORY}"
test ! -e "$1" || { echo 'Destination already exists'; exit 1; }
"$DESIGNWARE_HOME/bin/dw_vip_setup" -path "$1/apb" -e amba_svt/tb_apb_svt_uvm_basic_sys -svtb
"$DESIGNWARE_HOME/bin/dw_vip_setup" -path "$1/axi" -e amba_svt/tb_axi_svt_uvm_basic_sys -svtb
