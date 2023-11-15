ES=elasticsearch-8.11.1
ES_ARCHIVE=$ES-linux-x86_64.tar.gz
ES_ARCHIVE_SHA512=$ES_ARCHIVE.sha512

# elasticsearch fails to start when running as root
su jenkins -c "
    set -e
    cd /tmp 

    curl -O https://artifacts.elastic.co/downloads/elasticsearch/$ES_ARCHIVE
    curl -O https://artifacts.elastic.co/downloads/elasticsearch/$ES_ARCHIVE_SHA512

    sha512sum -c $ES_ARCHIVE_SHA512
    tar -xzf $ES_ARCHIVE

    # disable security
    cp -f ${WORKSPACE}/elasticsearch/elasticsearch.yml $ES/config/elasticsearch.yml
    # echo 'xpack.security.enabled: false' >> $ES/config/elasticsearch.yml

    ./$ES/bin/elasticsearch -d -p $ES.pid
"