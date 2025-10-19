###########
# BUILDER #
###########

# pull official base image
FROM python:3.10.12-buster as builder

# set work directory
WORKDIR /usr/src/app

#PYTHONDONTWRITEBYTECODE=1 tell Python to not write bytecode (.pyc) and __pycache__ directory on local env.
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# install dependencies
COPY ./requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt

#########
# FINAL #
#########

FROM python:3.10.12-buster

RUN apt-get update \
    # dependencies for building Python packages
    && apt-get install -y build-essential git netcat \
    # psycopg2 dependencies
    && apt-get install -y libpq-dev \
    # Translations dependencies
    && apt-get install -y gettext \
    # Additional dependencies
    && apt-get install -y procps \
    # cleaning up unused files
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system django \
    && adduser --system --ingroup django django

# install dependencies
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Requirements are installed here to ensure they will be cached.
COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# set work directory
WORKDIR /usr/src/app

COPY ./sv_carbon_removal .

COPY ./sv_carbon_removal/start.sh /usr/src/app/start.sh
COPY ./sv_carbon_removal/entrypoint.sh /usr/src/app/entrypoint.sh

RUN sed -i 's/\r$//g' /usr/src/app/start.sh
RUN chmod +x /usr/src/app/start.sh
RUN chown django /usr/src/app/start.sh

#entrypoint is used to process the line endings of the shell scripts, which converts Windows line endings to UNIX line endings.
RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh
RUN chmod +x /usr/src/app/entrypoint.sh
RUN chown django /usr/src/app/entrypoint.sh

RUN mkdir /usr/src/media
# RUN mkdir /usr/src/static

# # copy the static (pre-existing local for rest api drf interface, admin interface)
# COPY ./sv_carbon_removal/static /usr/src/static
# COPY ./sv_carbon_removal/media /usr/src/media

COPY ./user_id.json .
# COPY ./user_id_iqbal.json .

RUN chown -R django:django /usr/src/app

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]