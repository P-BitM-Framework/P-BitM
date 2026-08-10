FROM alpine:3.22

RUN apk add --no-cache squid ca-certificates

COPY squid.conf /etc/squid/squid.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh \
    && mkdir -p /var/log/squid /var/spool/squid /run \
    && chown -R squid:squid /var/log/squid /var/spool/squid /run

EXPOSE 3128
USER squid
ENTRYPOINT ["/entrypoint.sh"]
