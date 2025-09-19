# Generated migration for additional IO parameters and state flags

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gps_data', '0005_add_custom_command_support'),
    ]

    operations = [
        # Add analog inputs
        migrations.AddField(
            model_name='gpsrecord',
            name='analog_input_1',
            field=models.IntegerField(blank=True, help_text='IO009: Analog Input 1 (mV)', null=True),
        ),
        migrations.AddField(
            model_name='gpsrecord',
            name='analog_input_2',
            field=models.IntegerField(blank=True, help_text='IO006: Analog Input 2 (mV)', null=True),
        ),
        
        # Add accelerometer data
        migrations.AddField(
            model_name='gpsrecord',
            name='axis_x',
            field=models.IntegerField(blank=True, help_text='IO017: X axis value (mG)', null=True),
        ),
        migrations.AddField(
            model_name='gpsrecord',
            name='axis_y',
            field=models.IntegerField(blank=True, help_text='IO018: Y axis value (mG)', null=True),
        ),
        migrations.AddField(
            model_name='gpsrecord',
            name='axis_z',
            field=models.IntegerField(blank=True, help_text='IO019: Z axis value (mG)', null=True),
        ),
        
        # Add additional digital inputs
        migrations.AddField(
            model_name='gpsrecord',
            name='digital_input_2',
            field=models.BooleanField(blank=True, help_text='IO002: Digital Input 2', null=True),
        ),
        migrations.AddField(
            model_name='gpsrecord',
            name='digital_input_3',
            field=models.BooleanField(blank=True, help_text='IO003: Digital Input 3', null=True),
        ),
        
        # Add Dallas temperature sensors
        migrations.AddField(
            model_name='gpsrecord',
            name='dallas_temperature_1',
            field=models.IntegerField(blank=True, help_text='IO072: Dallas Temperature 1 (°C * 10)', null=True),
        ),
        migrations.AddField(
            model_name='gpsrecord',
            name='dallas_temperature_id_4',
            field=models.BigIntegerField(blank=True, help_text='IO071: Dallas Temperature ID 4', null=True),
        ),
        
        # Add P4 state flags (16 bytes binary)
        migrations.AddField(
            model_name='gpsrecord',
            name='security_state_flags_p4',
            field=models.BinaryField(blank=True, help_text='IO517: Security State Flags P4 (16 bytes binary)', max_length=16, null=True),
        ),
        migrations.AddField(
            model_name='gpsrecord',
            name='control_state_flags_p4',
            field=models.BinaryField(blank=True, help_text='IO518: Control State Flags P4 (16 bytes binary)', max_length=16, null=True),
        ),
        migrations.AddField(
            model_name='gpsrecord',
            name='indicator_state_flags_p4',
            field=models.BinaryField(blank=True, help_text='IO519: Indicator State Flags P4 (16 bytes binary)', max_length=16, null=True),
        ),
        
        # Update existing security_state_flags to 16 bytes binary for consistency
        migrations.AlterField(
            model_name='gpsrecord',
            name='security_state_flags',
            field=models.BinaryField(blank=True, help_text='IO132: Security State Flags (16 bytes binary)', max_length=16, null=True),
        ),
    ]
