"""Pydantic schemas: the shapes of data going in and out of the API.

They are separate from the ORM models on purpose: a model is how data is
*stored*, a schema is what the API *accepts/returns*. E.g. User has a
password_hash column, but UserOut never exposes it.
"""
