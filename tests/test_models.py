"""
Tests for CommandExecution model.

This is the RED phase of TDD - these tests should FAIL because the model
is not yet implemented.
"""
from django.test import TestCase
from django.utils import timezone

from django_managed_commands.models import CommandExecution


class CommandExecutionModelTest(TestCase):
    """Test suite for CommandExecution model."""

    def test_create_command_execution_with_all_fields(self):
        """Test creating a CommandExecution with all fields populated."""
        before = timezone.now()
        duration = 5.0  # Duration in seconds as float
        parameters = {"arg1": "value1", "flag": True}

        execution = CommandExecution.objects.create(
            command_name="test_command",
            success=True,
            parameters=parameters,
            output="Command output",
            error_message="",
            duration=duration,
            run_once=False
        )
        after = timezone.now()

        self.assertEqual(execution.command_name, "test_command")
        # Verify executed_at was automatically set (auto_now_add behavior)
        self.assertIsNotNone(execution.executed_at)
        self.assertGreaterEqual(execution.executed_at, before)
        self.assertLessEqual(execution.executed_at, after)
        self.assertTrue(execution.success)
        self.assertEqual(execution.parameters, parameters)
        self.assertEqual(execution.output, "Command output")
        self.assertEqual(execution.error_message, "")
        self.assertEqual(execution.duration, duration)
        self.assertFalse(execution.run_once)

    def test_command_name_field(self):
        """Test command_name CharField has max_length=255."""
        execution = CommandExecution.objects.create(
            command_name="a" * 255
        )
        self.assertEqual(len(execution.command_name), 255)

        # Verify field properties
        field = CommandExecution._meta.get_field('command_name')
        self.assertEqual(field.max_length, 255)

    def test_executed_at_auto_now_add(self):
        """Test executed_at is automatically set on creation."""
        before = timezone.now()
        execution = CommandExecution.objects.create(
            command_name="test_command"
        )
        after = timezone.now()

        self.assertIsNotNone(execution.executed_at)
        self.assertGreaterEqual(execution.executed_at, before)
        self.assertLessEqual(execution.executed_at, after)

        # Verify field has auto_now_add
        field = CommandExecution._meta.get_field('executed_at')
        self.assertTrue(field.auto_now_add)

    def test_success_default_true(self):
        """Test success field defaults to True."""
        execution = CommandExecution.objects.create(
            command_name="test_command"
        )
        self.assertTrue(execution.success)

        # Verify field default
        field = CommandExecution._meta.get_field('success')
        self.assertTrue(field.default)

    def test_parameters_jsonfield_default(self):
        """Test parameters JSONField defaults to None (nullable)."""
        execution = CommandExecution.objects.create(
            command_name="test_command"
        )
        # Parameters is nullable, so it defaults to None
        self.assertIsNone(execution.parameters)

    def test_parameters_accepts_dict(self):
        """Test parameters can store complex JSON data."""
        complex_params = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }

        execution = CommandExecution.objects.create(
            command_name="test_command",
            parameters=complex_params
        )

        # Refresh from database to ensure JSON serialization works
        execution.refresh_from_db()
        self.assertEqual(execution.parameters, complex_params)

    def test_output_field_blank(self):
        """Test output field can be blank."""
        execution = CommandExecution.objects.create(
            command_name="test_command"
        )
        self.assertEqual(execution.output, "")

        # Verify field allows blank
        field = CommandExecution._meta.get_field('output')
        self.assertTrue(field.blank)

    def test_error_message_field_blank(self):
        """Test error_message field can be blank."""
        execution = CommandExecution.objects.create(
            command_name="test_command"
        )
        self.assertEqual(execution.error_message, "")

        # Verify field allows blank
        field = CommandExecution._meta.get_field('error_message')
        self.assertTrue(field.blank)

    def test_duration_field_nullable(self):
        """Test duration field can be null."""
        execution = CommandExecution.objects.create(
            command_name="test_command"
        )
        self.assertIsNone(execution.duration)

        # Verify field allows null
        field = CommandExecution._meta.get_field('duration')
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

        # Test setting duration (as float in seconds)
        execution.duration = 10.0
        execution.save()
        execution.refresh_from_db()
        self.assertEqual(execution.duration, 10.0)

    def test_run_once_default_false(self):
        """Test run_once field defaults to False."""
        execution = CommandExecution.objects.create(
            command_name="test_command"
        )
        self.assertFalse(execution.run_once)

        # Verify field default
        field = CommandExecution._meta.get_field('run_once')
        self.assertFalse(field.default)

    def test_str_method(self):
        """Test __str__ returns meaningful string representation."""
        execution = CommandExecution.objects.create(
            command_name="test_command",
            success=True
        )
        str_repr = str(execution)

        # Should contain command name and some indication of status
        self.assertIn("test_command", str_repr)
        # Common patterns: "test_command - Success" or "test_command (success)"
        self.assertTrue(
            any(word in str_repr.lower() for word in ["success", "true", "✓"])
        )

    def test_ordering(self):
        """Test default ordering is by -executed_at (newest first)."""
        # Create executions with different timestamps
        old_execution = CommandExecution.objects.create(
            command_name="old_command"
        )

        # Small delay to ensure different timestamps
        import time
        time.sleep(0.01)

        new_execution = CommandExecution.objects.create(
            command_name="new_command"
        )

        # Query all executions
        executions = list(CommandExecution.objects.all())

        # Newest should be first
        self.assertEqual(executions[0].id, new_execution.id)
        self.assertEqual(executions[1].id, old_execution.id)

        # Verify Meta ordering
        self.assertEqual(
            CommandExecution._meta.ordering,
            ['-executed_at']
        )
