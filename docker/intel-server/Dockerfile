FROM alpine:3.20
RUN apk add --no-cache openssh-server && \
    adduser -D -s /sbin/nologin intel && \
    sed -i 's/^intel:!:/intel:*:/' /etc/shadow && \
    mkdir -p /data && chown intel:intel /data
COPY sshd_config /etc/ssh/sshd_config
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
