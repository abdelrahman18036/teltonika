# Generated manually for custom command support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gps_data', '0004_auto_20250709_0246'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devicecommand',
            name='command_type',
            field=models.CharField(choices=[('digital_output', 'Digital Output Stream'), ('can_control', 'CAN Control Stream'), ('custom', 'Custom Command')], max_length=20),
        ),
        migrations.AlterField(
            model_name='devicecommand',
            name='command_name',
            field=models.CharField(help_text='lock, unlock, mobilize, immobilize, or custom command name', max_length=50),
        ),
        migrations.AlterField(
            model_name='devicecommand',
            name='command_text',
            field=models.CharField(help_text='The actual command sent to device', max_length=200),
        ),
        migrations.AddField(
            model_name='devicecommand',
            name='is_custom_command',
            field=models.BooleanField(default=False, help_text='True if this is a custom command'),
        ),
    ]
