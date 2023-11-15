ES=elasticsearch-8.11.1
ES_ARCHIVE=$ES-linux-x86_64.tar.gz
ES_ARCHIVE_SHA512=$ES_ARCHIVE.sha512

set -e
su jenkins  # elasticsearch fails to start when running as root
whoami
cd /tmp

curl -O $ES_ARCHIVE https://artifacts.elastic.co/downloads/elasticsearch/$ES_ARCHIVE
curl -O $ES_ARCHIVE_SHA512 https://artifacts.elastic.co/downloads/elasticsearch/$ES_ARCHIVE_SHA512

sha512sum -c $ES_ARCHIVE_SHA512
tar -xzf $ES_ARCHIVE

# disable security
sed -i 's/xpack.security.enabled: true/xpack.security.enabled: false/g' $ES/config/elasticsearch.yml
export ELASTIC_XPACK_SECURITY_ENABLED=false
./$ES/bin/elasticsearch -d -p $ES.pid