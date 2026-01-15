#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    # Ensure PyMySQL is used as MySQLdb replacement early to avoid importing
    # a system-installed mysqlclient before the shim is registered.
    try:
        import pymysql
        pymysql.install_as_MySQLdb()
    except Exception:
        # If PyMySQL isn't installed yet, we'll let Django raise the appropriate
        # error later. This try/except prevents manage.py from crashing on import.
        pass
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
