FROM python:3.13.0
MAINTAINER fisher.yu <yu2hei@gmail.com>
WORKDIR /root/

COPY . /root/
RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
EXPOSE 5000
CMD ["python3", "app.py"]

RUN hash -r \
    && apt-get clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/share/man \
        /usr/share/doc \
        /usr/share/doc-base
