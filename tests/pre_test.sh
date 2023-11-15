ES=elasticsearch-8.11.1
ES_ARCHIVE=$ES-linux-x86_64.tar.gz
ES_ARCHIVE_SHA512=$ES_ARCHIVE.sha512

curl -o /tmp/$ES_ARCHIVE https://artifacts.elastic.co/downloads/elasticsearch/$ES_ARCHIVE
curl -o /tmp/$ES_ARCHIVE_SHA512 https://artifacts.elastic.co/downloads/elasticsearch/$ES_ARCHIVE_SHA512

sha512sum -c /tmp/$ES_ARCHIVE_SHA512
tar -xzf /tmp/$ES_ARCHIVE --directory /tmp/

# disable security
sed -i 's/xpack.security.enabled: true/xpack.security.enabled: false/g' /tmp/$ES/config/elasticsearch.yml
export ELASTIC_XPACK_SECURITY_ENABLED=false
/tmp/$ES/bin/elasticsearch -d -p /tmp/$ES.pid