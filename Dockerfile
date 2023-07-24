#
FROM python:3.9

#
WORKDIR /app

#
COPY ./requirements.txt /app/requirements.txt

#
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

#
COPY ./ /app

#
CMD ["uvicorn", "smauto.api.api:api", "--host", "0.0.0.0", "--port", "80"]

