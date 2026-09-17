from django.core.management.base import BaseCommand

from bills.prices import refresh_live_prices


class Command(BaseCommand):
    help = "Scrape live grocery prices from Google (with official retail fallback) and save them."

    def handle(self, *args, **options):
        payload = refresh_live_prices(progress=self.stdout.write)
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {payload.get('updated_count', 0)} prices at {payload.get('updated_at')}"
            )
        )
