from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from django_managed_commands.models import CommandExecution
from django_managed_commands.utils import (
    get_command_history,
    record_command_execution,
    should_run_command,
)


class UtilityFunctionsTest(TestCase):
    """Test suite for utility functions in django_managed_commands.utils"""

    def setUp(self):
        """Clear any existing command execution records before each test"""
        CommandExecution.objects.all().delete()

    # Tests for record_command_execution()
    def test_record_execution_creates_record(self):
        """Test that record_command_execution creates a CommandExecution record"""
        result = record_command_execution("test_command")

        self.assertIsNotNone(result)
        self.assertEqual(CommandExecution.objects.count(), 1)

        record = CommandExecution.objects.first()
        self.assertEqual(record.command_name, "test_command")

    def test_record_execution_with_all_parameters(self):
        """Test that all parameters are properly stored in the record"""
        test_params = {"key": "value", "number": 42}
        test_output = "Command executed successfully"
        test_error = "No errors"
        test_duration = 5.5

        result = record_command_execution(
            command_name="full_test_command",
            success=True,
            parameters=test_params,
            output=test_output,
            error_message=test_error,
            duration=test_duration,
            run_once=True,
        )

        self.assertEqual(result.command_name, "full_test_command")
        self.assertTrue(result.success)
        self.assertEqual(result.parameters, test_params)
        self.assertEqual(result.output, test_output)
        self.assertEqual(result.error_message, test_error)
        self.assertEqual(result.duration, test_duration)
        self.assertTrue(result.run_once)

    def test_record_execution_default_values(self):
        """Test that default parameter values work correctly"""
        result = record_command_execution("default_test")

        self.assertEqual(result.command_name, "default_test")
        self.assertTrue(result.success)  # Default is True
        self.assertIsNone(result.parameters)  # Default is None
        self.assertEqual(result.output, "")  # Default is empty string
        self.assertEqual(result.error_message, "")  # Default is empty string
        self.assertIsNone(result.duration)  # Default is None
        self.assertFalse(result.run_once)  # Default is False

    def test_record_execution_returns_instance(self):
        """Test that record_command_execution returns a CommandExecution instance"""
        result = record_command_execution("instance_test")

        self.assertIsInstance(result, CommandExecution)
        self.assertIsNotNone(result.pk)  # Should be saved to database

    # Tests for should_run_command()
    def test_should_run_command_no_previous_execution(self):
        """Test that should_run_command returns True when command has never been run"""
        result = should_run_command("never_run_command")

        self.assertTrue(result)

    def test_should_run_command_repeatable(self):
        """Test that should_run_command returns True when run_once=False"""
        # Create a previous execution with run_once=False
        CommandExecution.objects.create(
            command_name="repeatable_command",
            success=True,
            run_once=False,
        )

        result = should_run_command("repeatable_command")

        self.assertTrue(result)

    def test_should_run_command_run_once_executed(self):
        """Test that should_run_command returns False when run_once=True and already executed successfully"""
        # Create a successful execution with run_once=True
        CommandExecution.objects.create(
            command_name="run_once_command",
            success=True,
            run_once=True,
        )

        result = should_run_command("run_once_command")

        self.assertFalse(result)

    def test_should_run_command_run_once_failed(self):
        """Test that should_run_command returns True when run_once=True but previous run failed"""
        # Create a failed execution with run_once=True
        CommandExecution.objects.create(
            command_name="failed_once_command",
            success=False,
            run_once=True,
            error_message="Something went wrong",
        )

        result = should_run_command("failed_once_command")

        self.assertTrue(result)

    # Tests for get_command_history()
    def test_get_command_history_returns_queryset(self):
        """Test that get_command_history returns a QuerySet"""
        CommandExecution.objects.create(
            command_name="history_test",
            success=True,
        )

        result = get_command_history("history_test")

        self.assertEqual(result.__class__.__name__, "QuerySet")

    def test_get_command_history_filters_by_name(self):
        """Test that get_command_history only returns records for the specified command"""
        # Create records for different commands
        CommandExecution.objects.create(command_name="command_a", success=True)
        CommandExecution.objects.create(command_name="command_a", success=False)
        CommandExecution.objects.create(command_name="command_b", success=True)
        CommandExecution.objects.create(command_name="command_c", success=True)

        result = get_command_history("command_a")

        self.assertEqual(result.count(), 2)
        for record in result:
            self.assertEqual(record.command_name, "command_a")

    def test_get_command_history_limit(self):
        """Test that get_command_history respects the limit parameter"""
        # Create 15 records for the same command
        for i in range(15):
            CommandExecution.objects.create(
                command_name="limited_command",
                success=True,
            )

        result = get_command_history("limited_command", limit=5)

        self.assertEqual(result.count(), 5)

    def test_get_command_history_ordering(self):
        """Test that get_command_history returns records ordered by -executed_at (newest first)"""
        now = timezone.now()

        # Create records with different timestamps
        old_record = CommandExecution.objects.create(
            command_name="ordered_command",
            success=True,
        )
        old_record.executed_at = now - timedelta(hours=2)
        old_record.save()

        middle_record = CommandExecution.objects.create(
            command_name="ordered_command",
            success=True,
        )
        middle_record.executed_at = now - timedelta(hours=1)
        middle_record.save()

        new_record = CommandExecution.objects.create(
            command_name="ordered_command",
            success=True,
        )
        new_record.executed_at = now
        new_record.save()

        result = list(get_command_history("ordered_command"))

        self.assertEqual(result[0].pk, new_record.pk)
        self.assertEqual(result[1].pk, middle_record.pk)
        self.assertEqual(result[2].pk, old_record.pk)
