from django.core.management.base import BaseCommand
from store.models import Product

class Command(BaseCommand):
    help = 'Re-save Product images to trigger Cloudinary re-upload'

    def handle(self, *args, **options):
        updated = 0
        for product in Product.objects.all():
            if product.image:
                old_image = product.image
                product.image = old_image  # re-assign to trigger upload
                product.save()
                updated += 1
                self.stdout.write(self.style.SUCCESS(f'Updated: {product.name}'))
            else:
                self.stdout.write(f'Skipped (no image): {product.name}')

        self.stdout.write(self.style.SUCCESS(f'\nDone. Re-saved {updated} product(s).'))
