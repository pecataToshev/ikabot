from ikabot.command_line import start_command_line
from ikabot.migrations.migrate import apply_migrations

def main():
    print('Here in the __main__.py')

    apply_migrations()
    start_command_line('__main__.py')
