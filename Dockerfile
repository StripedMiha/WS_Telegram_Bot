FROM python:3.9

RUN mkdir -p /MigTeleBot/
COPY requirements.txt /MigTeleBot/
WORKDIR /MigTeleBot/
RUN pip install -r requirements.txt
COPY . /MigTeleBot/

ENV IS_DOCKER Yes
#EXPOSE 5000

CMD ["python", "Bot.py"]