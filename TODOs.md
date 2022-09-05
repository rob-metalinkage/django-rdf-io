# TODOs

## Django 4.X migration

There is an issue with the usage of ContentType.
In Django > 4 it should be used only at runtime:

s. https://stackoverflow.com/questions/43433406/sqlite3-operationalerror-no-such-table-django-content-type

This issue can occur if you have code that uses contenttypes database information at import time rather than at runtime. For example, if you added code that runs at the module level or class level along the lines of:

TERM_CONTENT_TYPE = ContentType.objects.get_for_model(Term)

but you only added this after running your initial migrations that created that content type tables, then the next person who runs the migrations on a fresh database will get this error.

In this case the solution is to move code like that into places that runs only when a method is called, like into a view or other method.



workaround :


    sqlite3 <DB filename> 

Create the table using the following command:

    CREATE TABLE IF
    NOT EXISTS "django_content_type" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "app_label" varchar(100) NOT NULL,
    "model" varchar(100) NOT NULL
    );

Finally run the migrations using the command below:

    python manage.py migrate --fake-initial



