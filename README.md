# django-search-example

This project is an example for using Django's full text search based on
PostgreSQL.

The version found in the main branch provides an application with a search
form. The actual search uses Django's `icontains` which on an SQL level maps
to `like` while ignoring the case of letters. This works only for simple
search requests and is very inefficient.

The search functionality is gradually improved in additional feature branches:

## Project set up

Before you can run the application in the main branch you need to install:

1. [Python 3.8+](https://www.python.org/downloads/)
2. [Docker](https://docs.docker.com/get-docker/)
   (used to run a PostgreSQL database server)

Next start downloading some ebooks:

```bash
sh scripts/rsync_gutenberg.sh
```

Downloading the entire library of Project Gutenberg will take hours. But
for testing this script only needs to run for a couple of minutes until it
downloaded a few dozen or hundreds of ebooks.

You can leave this running in the background in case you want a larger amount
of ebooks eventually.

Next, launch the docker container providing the PostgreSQL database server:

```bash
docker-compose up
```

While the server runs, you cannot enter new commands in the terminal, so open
a new one for the commands to follow. (Alternatively you could add the option
`--detach` to the above call.)

After that, set up the poetry environment and pre-commit hook:

```bash
sh scripts/setup_project.sh
```

Once this is finished, open a poetry shell:

```bash
poetry shell
```

Any further commands should be run in this shell.

Next, set up the database:

```bash
sh scripts/reset_local_database.sh
```

This creates or clears the database and loads a few ebooks into it.

## Running the local development server

Finally, you can run the local development server. Optionally you can
specify the port to avoid clashes with existing services:

```bash
python manage.py runserver 8078
```

To search, navigate to <http://127.0.0.1:8078/> and enter a single word
search term, for example "house". (Later branches allow more sophisticated
searches).

To browse the documents available, navigate to
<http://127.0.0.1:8078/admin/gutensearch/document/>. For the login, use
`admin` as username and `deMo.123` as password.

## Learning text search

After that, open the slides stored in
`Full text search with Django and PostgreSQL.odp` and work your way through
them. For each new feature introduced there is an educational
[pull request](https://github.com/roskakori/django-search-example/pulls)
showing the code needed to implement it (based on the previous feature
branch).
