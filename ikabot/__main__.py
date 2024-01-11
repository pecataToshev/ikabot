from ikabot.command_line import main
from ikabot.migrations.migrate import apply_migrations

print('Here in the __main__.py')

apply_migrations()
main('__main__.py')
