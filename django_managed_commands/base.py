"""
Base class for managed Django commands with automatic execution tracking.

This module provides the ManagedCommand base class that handles:
- Automatic timing of command execution
- Database transaction wrapping for atomicity
- Execution recording (success and failure)
- Run-once command support
"""

import time

from django.core.management.base import BaseCommand
from django.db import transaction

from .utils import record_command_execution, should_run_command


class ManagedCommand(BaseCommand):
    """
    Base class for Django management commands with automatic tracking.

    Subclass this instead of BaseCommand to get:
    - Automatic execution timing
    - Database transaction wrapping (all-or-nothing)
    - Execution recording in CommandExecution model
    - Run-once support via `run_once = True`
    - Built-in --dry-run flag (executes but rolls back transaction)

    Example:
        class Command(ManagedCommand):
            help = "My command description"
            run_once = False  # Set to True for one-time commands

            def execute_command(self, *args, **options):
                # Your command logic here - runs inside a transaction
                self.stdout.write("Doing work...")
                self.stdout.write(self.style.SUCCESS("Done!"))
    """

    # Set to True if this command should only run once successfully
    run_once = False

    # Override to customize command name, otherwise auto-derived from module path
    # e.g., "myapp.management.commands.my_command" -> "myapp.my_command"
    command_name = None

    # Options to exclude from serialization (non-JSON-serializable or internal)
    _non_serializable_options = (
        "stdout",
        "stderr",
        "no_color",
        "force_color",
        "skip_checks",
        "settings",
        "pythonpath",
        "traceback",
        "dry_run",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Execute command but roll back all database changes",
        )

    def get_command_name(self):
        """
        Returns the command name for tracking purposes.

        If `command_name` class attribute is set, uses that value.
        Otherwise, auto-derives from module path:
            myapp.management.commands.my_command -> myapp.my_command
        """
        if self.command_name:
            return self.command_name

        module = self.__class__.__module__
        parts = module.split(".")
        # Expected format: myapp.management.commands.command_name
        if len(parts) >= 4 and parts[-3:-1] == ["management", "commands"]:
            return f"{parts[-4]}.{parts[-1]}"
        return module  # Fallback to full module path

    def get_serializable_options(self, options):
        """Filter out non-serializable options for storage."""
        return {k: v for k, v in options.items() if k not in self._non_serializable_options}

    def handle(self, *args, **options):
        """
        Wraps execute_command with timing, transaction, and recording.

        This method:
        1. Checks run_once condition
        2. Starts timing
        3. Runs execute_command inside a database transaction
        4. Records execution (success or failure) outside the transaction
        5. Re-raises any exceptions after recording
        """
        cmd_name = self.get_command_name()
        dry_run = options.get("dry_run", False)

        # Check if command should run (respects run_once)
        if self.run_once and not should_run_command(cmd_name):
            self.stdout.write(
                self.style.WARNING(
                    f"Command {cmd_name} has already been executed successfully. Skipping execution (run_once=True)."
                )
            )
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - all database changes will be rolled back"))

        start_time = time.time()
        serializable_options = self.get_serializable_options(options)

        try:
            with transaction.atomic():
                result = self.execute_command(*args, **options)
                if dry_run:
                    transaction.set_rollback(True)

            duration = time.time() - start_time

            if not dry_run:
                record_command_execution(
                    command_name=cmd_name,
                    success=True,
                    parameters=serializable_options,
                    output=str(result) if result else "",
                    duration=duration,
                    run_once=self.run_once,
                )

            success_msg = f"Command {cmd_name} completed successfully in {duration:.2f}s"
            if dry_run:
                success_msg += " (dry run - changes rolled back)"
            self.stdout.write(self.style.SUCCESS(success_msg))
            return result

        except Exception as e:
            # Record failed execution (outside transaction - always recorded)
            duration = time.time() - start_time
            error_message = f"{type(e).__name__}: {str(e)}"

            if not dry_run:
                record_command_execution(
                    command_name=cmd_name,
                    success=False,
                    parameters=serializable_options,
                    error_message=error_message,
                    duration=duration,
                    run_once=self.run_once,
                )

            self.stdout.write(self.style.ERROR(f"Command {cmd_name} failed: {error_message}"))
            raise

    def execute_command(self, *args, **options):
        """
        Override this method with your command logic.

        This method runs inside a database transaction. If an exception is raised,
        all database changes are rolled back automatically.

        Args:
            *args: Positional arguments passed to the command
            **options: Options parsed from command line arguments

        Returns:
            Optional return value (will be converted to string and stored in output)

        Raises:
            Any exception will be caught, recorded, and re-raised
        """
        raise NotImplementedError("Subclasses must implement execute_command()")
