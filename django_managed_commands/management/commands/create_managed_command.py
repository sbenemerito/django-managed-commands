"""
Django management command: create_managed_command

Generates a new Django management command with built-in execution tracking.
Creates both the command file and a corresponding test file.
"""

from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """
    Generate a new Django management command with tracking boilerplate.

    This command creates:
    - A management command file with CommandExecution tracking
    - A test file with basic test cases
    - All necessary __init__.py files
    """

    help = "Generate a new Django management command with execution tracking"

    def add_arguments(self, parser):
        """
        Add command arguments.

        Arguments:
            app_name: Name of the Django app where command will be created
            command_name: Name of the management command to create
            --run-once: Set run_once=True in generated command
            --force: Overwrite existing files if they exist
        """
        parser.add_argument(
            "app_name",
            nargs=1,
            type=str,
            help="Django app name (must be in INSTALLED_APPS)",
        )
        parser.add_argument(
            "command_name",
            nargs=1,
            type=str,
            help="Name of the management command to create",
        )
        parser.add_argument(
            "--run-once",
            action="store_true",
            help="Set run_once=True to prevent duplicate executions",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files if they exist",
        )

    def handle(self, *args, **options):
        """
        Main command logic to generate management command files.

        Steps:
        1. Validate inputs (app exists, command name is valid)
        2. Find app directory
        3. Create directory structure
        4. Load templates
        5. Render templates with substitutions
        6. Write files
        7. Report success
        """
        # Extract arguments from options
        app_name = options["app_name"][0]
        command_name = options["command_name"][0]
        run_once = options.get("run_once", False)
        force = options.get("force", False)

        # ============================================
        # VALIDATION
        # ============================================

        # Validate app exists in INSTALLED_APPS
        try:
            app_config = apps.get_app_config(app_name)
        except LookupError:
            raise CommandError(
                f"App '{app_name}' not found in INSTALLED_APPS. "
                f"Make sure the app is installed and configured correctly."
            )

        # Validate command_name is a valid Python identifier
        if not command_name.isidentifier():
            raise CommandError(
                f"Command name '{command_name}' is not a valid Python identifier. "
                f"Use only letters, numbers, and underscores. "
                f"Cannot start with a number."
            )

        # ============================================
        # FIND APP DIRECTORY
        # ============================================

        app_path = Path(app_config.path)

        # ============================================
        # CREATE DIRECTORY STRUCTURE
        # ============================================

        # Create management/commands/ directories
        management_dir = app_path / "management"
        commands_dir = management_dir / "commands"
        tests_dir = app_path / "tests"

        # Create directories and __init__.py files
        management_dir.mkdir(parents=True, exist_ok=True)
        (management_dir / "__init__.py").touch(exist_ok=True)

        commands_dir.mkdir(parents=True, exist_ok=True)
        (commands_dir / "__init__.py").touch(exist_ok=True)

        # Create tests directory if it doesn't exist
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "__init__.py").touch(exist_ok=True)

        # ============================================
        # CHECK EXISTING FILES
        # ============================================

        command_file_path = commands_dir / f"{command_name}.py"
        test_file_path = tests_dir / f"test_{command_name}.py"

        if not force:
            if command_file_path.exists():
                raise CommandError(f"Command file already exists: {command_file_path}\nUse --force to overwrite.")
            if test_file_path.exists():
                raise CommandError(f"Test file already exists: {test_file_path}\nUse --force to overwrite.")

        # ============================================
        # LOAD TEMPLATES
        # ============================================

        # Find templates directory (relative to this file)
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        command_template_path = templates_dir / "command_template.py.txt"
        test_template_path = templates_dir / "test_template.py.txt"

        # Read templates
        try:
            with open(command_template_path, "r") as f:
                command_template = f.read()
        except FileNotFoundError:
            raise CommandError(f"Command template not found at {command_template_path}")

        try:
            with open(test_template_path, "r") as f:
                test_template = f.read()
        except FileNotFoundError:
            raise CommandError(f"Test template not found at {test_template_path}")

        # ============================================
        # RENDER TEMPLATES
        # ============================================

        # Generate class name (TitleCase from command_name)
        # e.g., 'my_command' -> 'MyCommand'
        class_name = "".join(word.capitalize() for word in command_name.split("_"))

        # Substitute placeholders in command template
        command_content = command_template.format(
            command_name=command_name,
            app_name=app_name,
            class_name=class_name,
        )

        # Handle run_once flag
        if run_once:
            # Replace 'run_once = False' with 'run_once = True'
            command_content = command_content.replace("run_once = False", "run_once = True")

        if run_once:
            run_behavior_test = """    def test_run_once_prevents_reexecution(self):
        call_command("{command_name}")
        first_execution = CommandExecution.objects.first()
        self.assertTrue(first_execution.success)

        out = StringIO()
        call_command("{command_name}", stdout=out)

        self.assertEqual(CommandExecution.objects.count(), 1)
        self.assertIn("Skipped", out.getvalue())""".format(command_name=command_name)
        else:
            run_behavior_test = """    def test_can_run_multiple_times(self):
        call_command("{command_name}")
        call_command("{command_name}")
        call_command("{command_name}")

        self.assertEqual(
            CommandExecution.objects.filter(command_name="{app_name}.{command_name}").count(),
            3,
        )""".format(command_name=command_name, app_name=app_name)

        # Substitute placeholders in test template
        test_content = test_template.format(
            command_name=command_name,
            app_name=app_name,
            class_name=class_name,
            run_behavior_test=run_behavior_test,
        )

        # ============================================
        # WRITE FILES
        # ============================================

        # Write command file
        with open(command_file_path, "w") as f:
            f.write(command_content)

        # Write test file
        with open(test_file_path, "w") as f:
            f.write(test_content)

        # ============================================
        # OUTPUT SUCCESS MESSAGE
        # ============================================

        self.stdout.write(self.style.SUCCESS("\nSuccessfully created management command!\n"))
        self.stdout.write(f"  Command: {command_file_path}")
        self.stdout.write(f"  Test:    {test_file_path}")
        self.stdout.write("\nNext steps:")
        self.stdout.write(f"  1. Edit {command_file_path} to add your command logic")
        self.stdout.write(f"  2. Update {test_file_path} with specific test cases")
        self.stdout.write(f"  3. Run: python manage.py {command_name}")
