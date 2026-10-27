from django.db import models


class CIEmailField(models.EmailField):
    """EmailField stored as PostgreSQL citext for case-insensitive uniqueness."""

    def db_type(self, connection):
        if connection.vendor == "postgresql":
            return "citext"
        return super().db_type(connection)


class CICharField(models.CharField):
    """CharField stored as PostgreSQL citext for case-insensitive uniqueness."""

    def db_type(self, connection):
        if connection.vendor == "postgresql":
            return "citext"
        return super().db_type(connection)
