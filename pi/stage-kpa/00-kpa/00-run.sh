#!/bin/bash -e
# pi-gen step: install the bridge, its service and the start-up helper into the image
install -d -m 755 "${ROOTFS_DIR}/opt/kpa-bridge"
install -m 644 files/kpa1500_sdr_bridge.py files/kpa1500_flex_emulation.py files/LICENSE "${ROOTFS_DIR}/opt/kpa-bridge/"
install -m 755 files/kpa-apply "${ROOTFS_DIR}/usr/local/sbin/kpa-apply"
install -m 644 files/kpa-bridge.service "${ROOTFS_DIR}/etc/systemd/system/kpa-bridge.service"
install -m 644 files/kpa-setup.txt "${ROOTFS_DIR}/boot/firmware/kpa-setup.txt"
echo 'OTHER_FLAGS=' > "${ROOTFS_DIR}/etc/kpa-bridge.conf"
on_chroot << CHEOF
id -u kpa >/dev/null 2>&1 || useradd -r -m -d /home/kpa -s /usr/sbin/nologin kpa
chown -R kpa:kpa /opt/kpa-bridge
systemctl enable kpa-bridge.service
systemctl enable avahi-daemon.service
CHEOF
