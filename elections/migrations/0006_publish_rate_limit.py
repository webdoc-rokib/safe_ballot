from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0005_election_publish_guard'),
    ]

    operations = [
        migrations.AddField(
            model_name='election',
            name='publish_attempts',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='election',
            name='publish_blocked_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
