"""
Tests for create_managed_command management command.
"""

import os
import shutil
import sys
import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

TEST_APP_NAME = "testapp"


class CreateManagedCommandTest(TestCase):
    """Test suite for create_managed_command management command."""

    def setUp(self):
        """Set up temporary test app directory for each test."""
        # Create a temporary directory for test apps
        self.test_dir = tempfile.mkdtemp()
        self.test_app_name = TEST_APP_NAME
        self.test_app_path = os.path.join(self.test_dir, self.test_app_name)

        # Create test app directory structure
        os.makedirs(self.test_app_path, exist_ok=True)

        # Create __init__.py to make it a valid Python package
        with open(os.path.join(self.test_app_path, "__init__.py"), "w") as f:
            f.write("")

        # Create tests directory
        self.test_tests_dir = os.path.join(self.test_app_path, "tests")
        os.makedirs(self.test_tests_dir, exist_ok=True)
        with open(os.path.join(self.test_tests_dir, "__init__.py"), "w") as f:
            f.write("")

        # Add test_dir to sys.path so testapp can be imported
        sys.path.insert(0, self.test_dir)

    def tearDown(self):
        """Clean up temporary test app directory after each test."""
        # Remove test_dir from sys.path
        if self.test_dir in sys.path:
            sys.path.remove(self.test_dir)

        # Remove testapp from sys.modules to force reimport
        modules_to_remove = [key for key in sys.modules.keys() if key.startswith(TEST_APP_NAME)]
        for module in modules_to_remove:
            del sys.modules[module]

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _get_command_path(self, command_name):
        """Helper to get expected command file path."""
        return os.path.join(self.test_app_path, "management", "commands", f"{command_name}.py")

    def _get_test_path(self, command_name):
        """Helper to get expected test file path."""
        return os.path.join(self.test_tests_dir, f"test_{command_name}.py")

    # ============================================
    # Basic Generation Tests
    # ============================================

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_creates_command_file(self):
        """Verify command file is created in correct location."""
        command_name = "mycommand"

        # Call the command
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Verify command file exists
        command_path = self._get_command_path(command_name)
        self.assertTrue(os.path.exists(command_path), f"Command file should exist at {command_path}")

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_creates_test_file(self):
        """Verify test file is created."""
        command_name = "mycommand"

        # Call the command
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Verify test file exists
        test_path = self._get_test_path(command_name)
        self.assertTrue(os.path.exists(test_path), f"Test file should exist at {test_path}")

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_creates_init_files(self):
        """Verify __init__.py files are created in management/commands/."""
        command_name = "mycommand"

        # Call the command
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Verify __init__.py in management/
        management_init = os.path.join(self.test_app_path, "management", "__init__.py")
        self.assertTrue(
            os.path.exists(management_init),
            f"__init__.py should exist at {management_init}",
        )

        # Verify __init__.py in management/commands/
        commands_init = os.path.join(self.test_app_path, "management", "commands", "__init__.py")
        self.assertTrue(
            os.path.exists(commands_init),
            f"__init__.py should exist at {commands_init}",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_command_file_has_managed_command(self):
        """Verify generated command imports and extends ManagedCommand."""
        command_name = "mycommand"

        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        self.assertIn(
            "from django_managed_commands.base import ManagedCommand",
            content,
            "Command should import ManagedCommand",
        )

        self.assertIn(
            "class Command(ManagedCommand):",
            content,
            "Command class should extend ManagedCommand",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_command_file_uses_managed_command_base(self):
        """Verify generated file extends ManagedCommand which provides tracking."""
        command_name = "mycommand"

        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        self.assertIn(
            "from django_managed_commands.base import ManagedCommand",
            content,
            "Command should import ManagedCommand which provides tracking",
        )

        self.assertIn(
            "class Command(ManagedCommand):",
            content,
            "Command should extend ManagedCommand for automatic tracking",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_test_file_has_testcase(self):
        """Verify generated test imports TestCase."""
        command_name = "mycommand"

        # Call the command
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Read generated test file
        test_path = self._get_test_path(command_name)
        with open(test_path, "r") as f:
            content = f.read()

        # Verify imports TestCase
        self.assertIn("from django.test import TestCase", content, "Test should import TestCase")

        # Verify imports call_command
        self.assertIn(
            "from django.core.management import call_command",
            content,
            "Test should import call_command",
        )

    # ============================================
    # Validation Tests
    # ============================================

    def test_requires_app_name_and_command_name(self):
        """Test missing arguments raise error."""
        # Test missing both arguments
        with self.assertRaises(CommandError) as cm:
            call_command("create_managed_command", stdout=StringIO())

        # The error message should indicate missing arguments
        error_msg = str(cm.exception).lower()
        self.assertTrue(
            "required" in error_msg or "argument" in error_msg,
            f"Error should mention required arguments: {error_msg}",
        )

    def test_validates_app_exists_in_installed_apps(self):
        """Test invalid app raises CommandError."""
        command_name = "mycommand"
        invalid_app = "nonexistent_app"

        with self.assertRaises(CommandError) as cm:
            call_command("create_managed_command", invalid_app, command_name, stdout=StringIO())

        # Error should mention the app not being in INSTALLED_APPS
        error_msg = str(cm.exception).lower()
        self.assertTrue(
            "installed_apps" in error_msg or "not found" in error_msg,
            f"Error should mention INSTALLED_APPS: {error_msg}",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_validates_command_name_is_valid_identifier(self):
        """Test invalid command names raise error."""
        invalid_names = [
            "my-command",  # hyphens not allowed
            "my command",  # spaces not allowed
            "123command",  # can't start with number
            "my.command",  # dots not allowed
        ]

        for invalid_name in invalid_names:
            with self.subTest(command_name=invalid_name):
                with self.assertRaises(CommandError) as cm:
                    call_command(
                        "create_managed_command",
                        self.test_app_name,
                        invalid_name,
                        stdout=StringIO(),
                    )

                # Error should mention invalid identifier
                error_msg = str(cm.exception).lower()
                self.assertTrue(
                    "invalid" in error_msg or "identifier" in error_msg,
                    f"Error should mention invalid identifier for '{invalid_name}': {error_msg}",
                )

    # ============================================
    # Options Tests
    # ============================================

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_run_once_flag(self):
        """Test --run-once flag generates run_once=True."""
        command_name = "mycommand"

        # Call the command with --run-once flag
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            run_once=True,
            stdout=StringIO(),
        )

        # Read generated command file
        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        # Verify run_once is set to True
        self.assertIn(
            "run_once = True",
            content,
            "Command should have run_once = True when --run-once flag is used",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_force_flag_overwrites_existing(self):
        """Test --force flag allows overwriting existing files."""
        command_name = "mycommand"

        # Create command first time
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Modify the generated file
        command_path = self._get_command_path(command_name)
        with open(command_path, "a") as f:
            f.write("\n# MODIFIED\n")

        # Verify modification exists
        with open(command_path, "r") as f:
            content_before = f.read()
        self.assertIn("# MODIFIED", content_before)

        # Create command again with --force
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            force=True,
            stdout=StringIO(),
        )

        # Verify file was overwritten (modification gone)
        with open(command_path, "r") as f:
            content_after = f.read()
        self.assertNotIn(
            "# MODIFIED",
            content_after,
            "File should be overwritten when --force is used",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_without_force_warns_on_existing(self):
        """Test warns without --force when file exists."""
        command_name = "mycommand"

        # Create command first time
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Try to create again without --force
        out = StringIO()
        with self.assertRaises(CommandError) as cm:
            call_command("create_managed_command", self.test_app_name, command_name, stdout=out)

        # Error should mention file exists or use --force
        error_msg = str(cm.exception).lower()
        self.assertTrue(
            "exists" in error_msg or "force" in error_msg,
            f"Error should mention file exists or --force flag: {error_msg}",
        )

    # ============================================
    # File Content Tests
    # ============================================

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_has_correct_class_name(self):
        """Verify Command class exists in generated file."""
        command_name = "mycommand"

        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        self.assertIn(
            "class Command(ManagedCommand):",
            content,
            "Generated file should contain Command class extending ManagedCommand",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_test_has_correct_class_name(self):
        """Verify test class is named correctly."""
        command_name = "mycommand"

        # Call the command
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Read generated test file
        test_path = self._get_test_path(command_name)
        with open(test_path, "r") as f:
            content = f.read()

        # Verify test class exists with correct naming pattern
        # Should be something like TestMycommandCommand or TestMyCommand
        self.assertTrue(
            "class Test" in content and "Command(TestCase):" in content,
            "Generated test should contain a Test class extending TestCase",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_has_execute_command_method(self):
        """Verify generated command has execute_command method."""
        command_name = "mycommand"

        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        self.assertIn("def execute_command(self", content, "Command should have execute_command method")

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_has_help_text(self):
        """Verify generated command has help attribute."""
        command_name = "mycommand"

        # Call the command
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Read generated command file
        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        # Verify help attribute exists
        self.assertIn("help = ", content, "Command should have help attribute")

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_command_includes_app_and_command_name(self):
        """Verify generated command includes app and command name in content."""
        command_name = "mycommand"

        # Call the command
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Read generated command file
        command_path = self._get_command_path(command_name)
        with open(command_path, "r") as f:
            content = f.read()

        # Verify app name and command name appear in the file
        # (likely in command_name variable or comments)
        self.assertTrue(
            self.test_app_name in content or command_name in content,
            "Generated command should reference app or command name",
        )

    @override_settings(INSTALLED_APPS=["django_managed_commands", TEST_APP_NAME])
    def test_generated_test_imports_command_execution_model(self):
        """Verify generated test imports CommandExecution model."""
        command_name = "mycommand"

        # Call the command
        call_command(
            "create_managed_command",
            self.test_app_name,
            command_name,
            stdout=StringIO(),
        )

        # Read generated test file
        test_path = self._get_test_path(command_name)
        with open(test_path, "r") as f:
            content = f.read()

        # Verify imports CommandExecution
        self.assertIn(
            "from django_managed_commands.models import CommandExecution",
            content,
            "Test should import CommandExecution model",
        )

    # TODO: Generation of command with flags
