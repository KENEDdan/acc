from django.core.validators import FileExtensionValidator

IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']

validate_image_extension = FileExtensionValidator(
    allowed_extensions=IMAGE_EXTENSIONS,
    message="Unsupported image type. Allowed: JPG, JPEG, PNG, WEBP.",
)
