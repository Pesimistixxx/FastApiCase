FROM alpine:latest

RUN apk add --no-cache postgresql-client bash cronie

COPY db_cleaner/cleaner.sh /usr/local/bin/cleanup.sh
RUN chmod +x /usr/local/bin/cleanup.sh

COPY db_cleaner/cleaner-cron /etc/crontabs/root

CMD ["crond", "-f"]