from django.core.management.base import BaseCommand

from apps.documents import services


class Command(BaseCommand):
    help = "Register files in the documents folder in the database; --reindex also rebuilds the index."

    def add_arguments(self, parser):
        parser.add_argument("--reindex", action="store_true", help="rebuild the whole search index")

    def handle(self, *args, **opts):
        if opts["reindex"]:
            services.start_reindex(background=False)
            self.stdout.write(self.style.SUCCESS("Index rebuilt."))
        else:
            n = services.sync_from_folder()
            self.stdout.write(self.style.SUCCESS(f"Registered {n} new document(s)."))
