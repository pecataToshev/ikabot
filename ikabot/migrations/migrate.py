import os

from yoyo import get_backend, read_migrations

from ikabot import config


def apply_migrations():
    print('Applying db migrations')
    db_uri = f'sqlite:///{config.DB_FILE}'
    migrations_dir = os.path.dirname(__file__)

    backend = get_backend(db_uri)
    migrations = read_migrations(migrations_dir)

    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))

    print('DB migrations applied')
