from django.core.management.base import BaseCommand
from store.models import Product
from cloudinary.uploader import upload
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Upload local product images to Cloudinary'

    def handle(self, *args, **options):
        common_exts = ['.jpg', '.jpeg', '.png', '.webp']
        media_root = os.path.join(settings.BASE_DIR, 'media')

        for product in Product.objects.all():
            if product.image:
                filename = os.path.splitext(str(product.image))[0]  # 'products/grocery5'

                # Try different extensions
                for ext in common_exts:
                    full_path = os.path.join(media_root, filename + ext)
                    if os.path.isfile(full_path):
                        with open(full_path, 'rb') as f:
                            result = upload(f, folder="products/")
                            product.image = result['public_id']
                            product.save()
                            self.stdout.write(self.style.SUCCESS(f"✅ Uploaded: {product.name}"))
                        break
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️ File not found for: {product.name}"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ No image for: {product.name}"))
