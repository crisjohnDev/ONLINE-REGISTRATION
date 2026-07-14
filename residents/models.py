from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone

# Create your models here.
class Residents(models.Model):

    class DocumentType(models.TextChoices):
        NEW_REGISTRATION = "new_registration", "New Registration"
        UPDATE = "update", "Update"
        TRANSFER = "transfer", "Transfer"
        REACTIVATION = "reactivation", "Reactivation"
        REINSTATEMENT = "reinstatement", "Reinstatement"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PRE_APPROVED = "pre-approved", "Pre-approved"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DUPLICATION = "duplication", "Duplication"

    tracking_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True
    )

    full_name = models.CharField(max_length=200)

    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices
    )

    document = models.FileField(
        upload_to="resident_documents/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "doc",
                    "docx",
                    "jpg",
                    "jpeg",
                    "png"
                ]
            )
        ]
    )

    thumb_mark = models.ImageField(
        upload_to="thumb_marks/",
        blank=True,
        null=True
    )

    biometric_date = models.DateTimeField(
        blank=True,
        null=True
    )


    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if not self.tracking_number:

            today = timezone.now().strftime("%Y%m%d")

            last = Residents.objects.filter(
                tracking_number__startswith=f"PIO-{today}"
            ).order_by("-tracking_number").first()

            if last:
                number = int(last.tracking_number.split("-")[-1]) + 1
            else:
                number = 1

            self.tracking_number = f"PIO-{today}-{number:04d}"

        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "full_name",
                    "document_type"
                ],
                condition=models.Q(
                    status__in=[
                        "pending",
                        "pre-approved",
                        "approved"
                    ]
                ),
                name="unique_active_resident_application"
            )
        ]

    def __str__(self):
        return f"{self.tracking_number} - {self.full_name}"