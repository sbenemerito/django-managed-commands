"""
End-to-end integration tests for command tracking workflow.

This test suite verifies the complete workflow: generate command → run command → verify tracking works.
Tests ensure that generated commands properly integrate with the CommandExecution tracking system.
"""

import importlib
import os
import shutil
import sys
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from django_managed_commands.models import CommandExecution

TEST_APP_NAME = "testapp"


class CommandTrackingIntegrationTest(TestCase):
    """Integration tests for command generation and execution tracking."""

    def setUp(self):
        """Set up temporary test app and generate a test command."""
        # Create a temporary directory for test apps
        self.test_dir = tempfile.mkdtemp()
        self.test_app_name = TEST_APP_NAME
        self.test_app_path = os.path.join(self.test_dir, self.test_app_name)

        # Create test app directory structure
        os.makedirs(self.test_app_path, exist_ok=True)

        # Create __init__.py to make it a valid Python package
        with open(os.path.join(self.test_app_path, "__init__.py"), "w") as f:
            f.write("")

        # Add test_dir to sys.path so testapp can be imported
        sys.path.insert(0, self.test_dir)

        # Clear any existing CommandExecution records
        CommandExecution.objects.all().delete()

    def tearDown(self):
        """Clean up temporary test app directory and CommandExecution records."""
        # Remove test_dir from sys.path
        if self.test_dir in sys.path:
            sys.path.remove(self.test_dir)

        # Remove testapp from sys.modules to force reimport
        modules_to_remove = [
            key for key in sys.modules.keys() if key.startswith(TEST_APP_NAME)
        ]
        for module in modules_to_remove:
            del sys.modules[module]

        # Clean up temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        # Clean up CommandExecution records
        CommandExecution.objects.all().delete()

    def _generate_command(self, command_name, run_once=False):
        """Helper to generate a test command."""
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            run_once=run_once,
            stdout=StringIO(),
        )

    def _get_command_path(self, command_name):
        """Helper to get command file path."""
        return os.path.join(
            self.test_app_path, "management", "commands", f"{command_name}.py"
        )

    def _load_command_class(self, command_name):
        """Helper to dynamically load a generated command class."""
        # Import the command module
        module_path = f"{self.test_app_name}.management.commands.{command_name}"

        # Remove from sys.modules if already loaded to force fresh import
        if module_path in sys.modules:
            del sys.modules[module_path]

        # Import the module
        module = importlib.import_module(module_path)

        # Return the Command class
        return module.Command()

    # ============================================
    # Integration Tests
    # ============================================

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_records_execution(self):
        """Verify generated command creates CommandExecution record when run."""
        command_name = "test_tracking_command"
        full_command_name = f"{self.test_app_name}.{command_name}"

        # Generate the command
        self._generate_command(command_name)

        # Verify no executions exist yet
        self.assertEqual(
            CommandExecution.objects.filter(command_name=full_command_name).count(),
            0,
            "No executions should exist before running command",
        )

        # Load and run the generated command
        command = self._load_command_class(command_name)
        call_command(command, stdout=StringIO())

        # Verify execution was recorded
        executions = CommandExecution.objects.filter(command_name=full_command_name)
        self.assertEqual(
            executions.count(),
            1,
            "Exactly one execution should be recorded after running command",
        )

        # Verify the execution has the correct command name
        execution = executions.first()
        self.assertEqual(
            execution.command_name,
            full_command_name,
            "Recorded execution should have correct command name",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_records_success(self):
        """Verify generated command records success=True for successful execution."""
        command_name = "test_success_command"
        full_command_name = f"{self.test_app_name}.{command_name}"

        # Generate and run the command
        self._generate_command(command_name)
        command = self._load_command_class(command_name)
        call_command(command, stdout=StringIO())

        # Verify success is True
        execution = CommandExecution.objects.get(command_name=full_command_name)
        self.assertTrue(
            execution.success, "Successful command execution should have success=True"
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_records_parameters(self):
        """Verify generated command records parameters when command has arguments."""
        command_name = "test_params_command"

        # Generate the command
        self._generate_command(command_name)

        # Modify the generated command to accept arguments
        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        # Replace the add_arguments method with one that has a real argument
        # Find the existing add_arguments method and replace it
        add_args_start = content.find("def add_arguments(self, parser):")
        if add_args_start != -1:
            # Find the end of the add_arguments method (next def or handle method)
            add_args_end = content.find("def handle(self", add_args_start)

            # Replace the add_arguments method
            new_add_arguments = '''def add_arguments(self, parser):
        """Add custom command arguments."""
        parser.add_argument(
            '--test-arg',
            type=str,
            default='default_value',
            help='Test argument for parameter tracking'
        )

    '''
            content = (
                content[:add_args_start] + new_add_arguments + content[add_args_end:]
            )

            with open(command_path, "w") as f:
                f.write(content)

        # Load and run the command with a parameter
        command = self._load_command_class(command_name)
        call_command(command, test_arg="test_value", stdout=StringIO())

        # Verify parameters were recorded
        full_command_name = f"{self.test_app_name}.{command_name}"
        execution = CommandExecution.objects.get(command_name=full_command_name)
        self.assertIsNotNone(
            execution.parameters, "Command execution should record parameters"
        )
        self.assertIn(
            "test_arg", execution.parameters, "Parameters should include test_arg"
        )
        self.assertEqual(
            execution.parameters["test_arg"],
            "test_value",
            "Parameter value should be recorded correctly",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_records_duration(self):
        """Verify generated command records execution duration."""
        command_name = "test_duration_command"
        full_command_name = f"{self.test_app_name}.{command_name}"

        # Generate and run the command
        self._generate_command(command_name)
        command = self._load_command_class(command_name)
        call_command(command, stdout=StringIO())

        # Verify duration is set
        execution = CommandExecution.objects.get(command_name=full_command_name)
        self.assertIsNotNone(
            execution.duration, "Command execution should record duration"
        )
        self.assertGreaterEqual(
            execution.duration, 0, "Duration should be non-negative"
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_run_once_command_prevents_second_run(self):
        """Verify command generated with --run-once prevents re-execution."""
        command_name = "test_run_once_command"
        full_command_name = f"{self.test_app_name}.{command_name}"

        # Generate command with run_once=True
        self._generate_command(command_name, run_once=True)

        # Load the command
        command = self._load_command_class(command_name)

        # Run the command first time
        call_command(command, stdout=StringIO())

        # Verify first execution was recorded
        first_execution = CommandExecution.objects.get(command_name=full_command_name)
        self.assertTrue(
            first_execution.run_once, "First execution should have run_once=True"
        )
        self.assertTrue(first_execution.success, "First execution should be successful")

        # Try to run the command again
        out = StringIO()
        call_command(command, stdout=out)
        output = out.getvalue()

        # Verify command was skipped (should output a message about already running)
        self.assertIn(
            "already", output.lower(), "Second run should indicate command already ran"
        )

        # Verify only one execution was recorded
        executions = CommandExecution.objects.filter(command_name=full_command_name)
        self.assertEqual(
            executions.count(),
            1,
            "Only one execution should be recorded for run_once command",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_failed_command_records_error(self):
        """Verify failed command execution records error information."""
        command_name = "test_error_command"
        full_command_name = f"{self.test_app_name}.{command_name}"

        # Generate the command
        self._generate_command(command_name)

        # Modify the generated command to raise an exception in the logic section
        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        # Find the "YOUR LOGIC HERE" section and inject an error
        logic_marker = "# YOUR LOGIC HERE"
        if logic_marker in content:
            # Insert error after the marker
            content = content.replace(
                logic_marker,
                logic_marker
                + '\n            raise ValueError("Test error for integration testing")',
            )

            with open(command_path, "w") as f:
                f.write(content)

        # Load and run the command and expect it to fail
        command = self._load_command_class(command_name)
        try:
            call_command(command, stdout=StringIO())
        except Exception:
            pass  # Expected to fail

        # Verify error was recorded
        execution = CommandExecution.objects.get(command_name=full_command_name)
        self.assertFalse(
            execution.success, "Failed command execution should have success=False"
        )
        self.assertNotEqual(
            execution.error_message, "", "Failed command should record error message"
        )
        self.assertIn(
            "Test error",
            execution.error_message,
            "Error message should contain the exception message",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_multiple_executions_tracked_separately(self):
        """Verify multiple executions of same command are tracked separately."""
        command_name = "test_multiple_command"
        full_command_name = f"{self.test_app_name}.{command_name}"

        # Generate the command (without run_once)
        self._generate_command(command_name, run_once=False)

        # Load the command
        command = self._load_command_class(command_name)

        # Run the command multiple times
        call_command(command, stdout=StringIO())
        call_command(command, stdout=StringIO())
        call_command(command, stdout=StringIO())

        # Verify all executions were recorded
        executions = CommandExecution.objects.filter(command_name=full_command_name)
        self.assertEqual(
            executions.count(), 3, "All three executions should be recorded separately"
        )

        # Verify all are successful
        for execution in executions:
            self.assertTrue(execution.success, "All executions should be successful")

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_has_executed_at_timestamp(self):
        """Verify generated command records execution timestamp."""
        command_name = "test_timestamp_command"
        full_command_name = f"{self.test_app_name}.{command_name}"

        # Generate and run the command
        self._generate_command(command_name)
        command = self._load_command_class(command_name)
        call_command(command, stdout=StringIO())

        # Verify executed_at is set
        execution = CommandExecution.objects.get(command_name=full_command_name)
        self.assertIsNotNone(
            execution.executed_at, "Command execution should have executed_at timestamp"
        )
