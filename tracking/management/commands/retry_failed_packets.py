from django.core.management.base import BaseCommand
from tracking.database_manager import db_manager


class Command(BaseCommand):
    help = 'Retry processing failed Teltonika packets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-attempts',
            type=int,
            default=5,
            help='Maximum number of retry attempts (default: 5)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of packets to process in one batch (default: 100)',
        )

    def handle(self, *args, **options):
        max_attempts = options['max_attempts']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting retry process with max attempts: {max_attempts}')
        )
        
        results = db_manager.retry_failed_packets(max_attempts)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Retry completed: {results["processed"]} processed, {results["failed"]} failed'
            )
        ) 