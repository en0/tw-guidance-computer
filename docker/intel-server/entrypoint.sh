#!/bin/sh
chown root:root /data
chmod 755 /data
mkdir -p /data/intel
chown intel:intel /data/intel
ssh-keygen -A
exec /usr/sbin/sshd -D -e
