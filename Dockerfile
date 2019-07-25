
FROM python:3.6

WORKDIR /ntc

ADD ./ntc_tesuto.py ntc_tesuto.py
ADD ./requirements.txt requirements.txt

RUN pip install -r requirements.txt

CMD [ "python", "ntc_tesuto.py" ]
