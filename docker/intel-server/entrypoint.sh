#!/bin/sh
chown root:root /data
chmod 755 /data
mkdir -p /data/intel
chown intel:intel /data/intel
cp /etc/tw-intel/keys /etc/tw-intel/authorized_keys
chmod 644 /etc/tw-intel/authorized_keys
chown root:root /etc/tw-intel/authorized_keys
ssh-keygen -A
exec /usr/sbin/sshd -D -e
