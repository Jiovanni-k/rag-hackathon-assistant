"""Create (or reset) the demo accounts so judges can log in right after `migrate`.

    python manage.py create_demo_accounts

Passwords can be overridden with DEMO_STUDENT_PASSWORD / DEMO_ADMIN_PASSWORD in .env.
These are demo accounts with no real personal data; change or delete them in production.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset the demo student and admin accounts."

    def handle(self, *args, **options):
        User = get_user_model()
        accounts = [  # username, password, is_staff/superuser
            ("student", settings.DEMO_STUDENT_PASSWORD, False),
            ("admin", settings.DEMO_ADMIN_PASSWORD, True),
        ]
        for username, password, is_admin in accounts:
            user, created = User.objects.get_or_create(username=username)
            user.email = f"{username}@demo.local"
            user.is_staff = user.is_superuser = is_admin
            user.set_password(password)
            user.save()
            action = "Created" if created else "Reset"
            self.stdout.write(self.style.SUCCESS(f"{action} {username!r} (password: {password})"))
