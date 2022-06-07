# django-search-example

This project is an example for using Django's full text search based on
PostgreSQL.

The version found in the main branch provides an application with a search
form. The actual search uses Django's `icontains` which on an SQL level maps
to `like` while ignoring the case of letters. This works only for simple
search requests and is very inefficient.

The search functionality is gradually improved in additional feature branches:

TODO: Add branches and issues
