from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
        ('file_upload', '0004_fileshare'),
    ]

    operations = [
        migrations.AddField(
            model_name='folder',
            name='organization',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.deletion.CASCADE, related_name='folders', to='authentication.organization'),
        ),
    ]

