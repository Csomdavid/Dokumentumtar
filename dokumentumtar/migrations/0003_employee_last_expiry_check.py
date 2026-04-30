from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dokumentumtar', '0002_document_file_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='last_expiry_check',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
