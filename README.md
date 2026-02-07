# django-managed-commands

[![PyPI version](https://img.shields.io/pypi/v/django-managed-commands?v=1)](https://pypi.org/project/django-managed-commands/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-managed-commands?v=1)](https://pypi.org/project/django-managed-commands/)
[![Django versions](https://img.shields.io/badge/django-3.2+-blue)](https://pypi.org/project/django-managed-commands/)
[![License](https://img.shields.io/pypi/l/django-managed-commands?v=1)](https://github.com/sbenemerito/django-managed-commands/blob/main/LICENSE)
[![CI](https://github.com/sbenemerito/django-managed-commands/actions/workflows/ci.yml/badge.svg)](https://github.com/sbenemerito/django-managed-commands/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sbenemerito/django-managed-commands/graph/badge.svg)](https://codecov.io/gh/sbenemerito/django-managed-commands)

## Overview

django-managed-commands is a Django library that provides robust tracking and management of Django management commands.

It helps prevent migration-related issues by tracking command execution history, provides standardized testing utilities, and offers a comprehensive API for managing command execution in your Django projects.

### Do you need this?

Too many times I've been involved in projects where somebody creates a management command and:
- it's supposed to be ran only once, but there are no guard rails to enforce that
  - doing a `call_command()` inside an empty DB migration doesn't always work because when there are field changes later on, this raises exceptions
- we do not certainly know if it was already ran (especially difficult for multi-tenant projects)
- no unit tests were written to properly test side-effects

If you are on the same boat, then the answer is probably yes.

Also because we had something similar in a team I was previously involved in, and I thought it was nice to have this in Django projects I'm currently working on. <sub>Shoutout to the guys at Linkers: Suzuki R., Yokoyama I., Nathan W., Onodera Y.</sub>

## Installation

1) Install the package via pip:

```bash
pip install django-managed-commands
```

or via uv:

```bash
uv add django-managed-commands
```

2) Add `django_managed_commands` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'django_managed_commands',
]
```

3) Run migrations to create the necessary database tables:

```bash
python manage.py migrate django_managed_commands
```

## Quick Start

Generate a new tracked management command using the built-in generator:

```bash
# Generate a command in your Django app
python manage.py create_managed_command myapp my_command

# Generate a run-once command (prevents duplicate executions)
python manage.py create_managed_command myapp setup_initial_data --run-once
```

where `myapp` is the name of the Django app you want to add the management command into, and `my_command` or `setup_initial_data` is the command name.

This creates a command file at `myapp/management/commands/my_command.py` with built-in execution tracking.

## Usage

### Creating a standard command

Generate a command that tracks every execution:

```bash
python manage.py create_managed_command myapp send_notifications
```

This creates `myapp/management/commands/send_notifications.py`:

```python
from django_managed_commands.base import ManagedCommand


class Command(ManagedCommand):
    """send_notifications management command."""

    help = "send_notifications command - add your description here"
    run_once = False

    def execute_command(self, *args, **options):
        # Your command logic here
        self.stdout.write("Sending notifications...")
        
        self.stdout.write(self.style.SUCCESS("send_notifications completed successfully"))
```

The `ManagedCommand` base class automatically handles:
- **Execution tracking**: Records success/failure in `CommandExecution` model
- **Timing**: Measures and stores execution duration
- **Database transactions**: Your logic runs inside `transaction.atomic()` - if an exception is raised, all database changes are rolled back
- **Error recording**: Failures are logged with error messages before re-raising

### Creating a run-once command

Generate a command that only executes once successfully:

```bash
python manage.py create_managed_command myapp setup_initial_data --run-once
```

The generated command includes automatic duplicate prevention:

```python
from django_managed_commands.base import ManagedCommand


class Command(ManagedCommand):
    """One-time setup command."""

    help = "setup_initial_data command"
    run_once = True  # Prevents duplicate executions

    def execute_command(self, *args, **options):
        # Your one-time setup logic here
        self.stdout.write(self.style.SUCCESS("Setup complete"))
```

When `run_once=True`, the command automatically checks execution history and skips if already run successfully.

### Viewing execution history in Django admin

django-managed-commands automatically registers the `CommandExecution` model in Django admin. Access it at `/admin/django_managed_commands/commandexecution/`:

- View all command executions with timestamps
- Filter by command name, success status, or date
- Search by command name or error messages
- See execution duration, parameters, and output for each run

### Programmatically accessing command history

Query command execution history using the provided utility functions:

```python
from django_managed_commands.utils import get_command_history
from django_managed_commands.models import CommandExecution

# Get last 10 executions of a specific command
history = get_command_history('myapp.send_notifications', limit=10)
for execution in history:
    print(f"{execution.executed_at}: {'Success' if execution.success else 'Failed'}")
    print(f"  Duration: {execution.duration}s")
    print(f"  Output: {execution.output}")

# Query all failed executions
failed_commands = CommandExecution.objects.filter(success=False)
for cmd in failed_commands:
    print(f"{cmd.command_name} failed at {cmd.executed_at}")
    print(f"  Error: {cmd.error_message}")

# Check if a command has ever run successfully
latest = CommandExecution.objects.filter(
    command_name='myapp.setup_initial_data',
    success=True
).first()
if latest:
    print(f"Last successful run: {latest.executed_at}")
else:
    print("Command has never run successfully")

# Get execution statistics
from django.db.models import Avg, Count
stats = CommandExecution.objects.filter(
    command_name='myapp.send_notifications'
).aggregate(
    total_runs=Count('id'),
    avg_duration=Avg('duration'),
    success_count=Count('id', filter=models.Q(success=True))
)
print(f"Total runs: {stats['total_runs']}")
print(f"Average duration: {stats['avg_duration']:.2f}s")
print(f"Success rate: {stats['success_count'] / stats['total_runs'] * 100:.1f}%")
```

### Using ManagedCommand base class

The recommended approach is to extend `ManagedCommand`:

```python
from django_managed_commands.base import ManagedCommand


class Command(ManagedCommand):
    help = "Process data with automatic tracking"
    
    # Optional: override command_name (auto-derived from module path if not set)
    # command_name = "myapp.custom_name"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def execute_command(self, *args, **options):
        # This runs inside a database transaction
        limit = options["limit"]
        processed = self.do_work(limit)
        self.stdout.write(f"Processed {processed} items")
        return processed  # Optional: return value is stored in execution record

    def do_work(self, limit):
        # Your implementation
        return 42
```

### Manual command tracking

For existing commands or special cases, you can manually track execution:

```python
import time
from django.core.management.base import BaseCommand
from django_managed_commands.utils import record_command_execution


class Command(BaseCommand):
    help = "Custom command with manual tracking"

    def handle(self, *args, **options):
        command_name = "myapp.custom_command"
        start_time = time.time()

        try:
            result = self.do_work()
            record_command_execution(
                command_name=command_name,
                success=True,
                parameters={"option": options.get("option")},
                output=f"Processed {result} items",
                duration=time.time() - start_time,
            )
        except Exception as e:
            record_command_execution(
                command_name=command_name,
                success=False,
                error_message=str(e),
                duration=time.time() - start_time,
            )
            raise

    def do_work(self):
        return 42
```

## Configuration

### Run-once Behavior

Commands can be configured to run only once successfully by setting `run_once=True`:

```python
class Command(ManagedCommand):
    run_once = True  # Command will only execute once successfully

    def execute_command(self, *args, **options):
        # Your one-time logic here
        pass
```

**How it works:**

1. Before execution, the base class checks the command history
2. If a successful execution with `run_once=True` exists, the command is skipped
3. If the previous execution failed, the command will run again
4. If no previous execution exists, the command runs normally

**Use cases for run-once commands:**

- Initial data setup or seeding
- One-time database migrations
- System initialization tasks
- Feature flag setup
- Configuration deployment

### Transaction Behavior

All commands extending `ManagedCommand` run inside a database transaction:

```python
class Command(ManagedCommand):
    def execute_command(self, *args, **options):
        # All database operations here are atomic
        User.objects.create(username="alice")
        Profile.objects.create(user=user)  # If this fails, User creation is rolled back
```

**Key points:**

- Your `execute_command` logic runs inside `transaction.atomic()`
- If any exception is raised, all database changes are rolled back
- Execution recording happens *outside* the transaction, so failures are always logged
- This ensures data consistency without manual transaction management

### Tracking Behavior

All command executions are automatically tracked with the following information:

- **command_name**: Unique identifier for the command (e.g., `myapp.my_command`)
- **executed_at**: Timestamp when the command started
- **success**: Boolean indicating if the command completed successfully
- **parameters**: JSON field storing command arguments and options
- **output**: Standard output from the command
- **error_message**: Error details if the command failed
- **duration**: Execution time in seconds
- **run_once**: Whether this command should only run once

### Database Configuration

The `CommandExecution` model uses Django's default database. No special configuration is required. The model includes:

- Automatic timestamp tracking (`auto_now_add=True`)
- JSON field for flexible parameter storage
- Indexed ordering by execution time (newest first)
- Admin interface integration

### Integration with Existing Projects

To add tracking to existing commands:

1. **Option A: Extend ManagedCommand (recommended)**
   ```python
   # Before
   from django.core.management.base import BaseCommand

   class Command(BaseCommand):
       def handle(self, *args, **options):
           # Your logic
           pass

   # After
   from django_managed_commands.base import ManagedCommand

   class Command(ManagedCommand):
       def execute_command(self, *args, **options):
           # Your logic (now with automatic tracking + transactions)
           pass
   ```

2. **Option B: Use the generator with --force**
   ```bash
   python manage.py create_managed_command myapp existing_command --force
   ```

3. **Option C: Manual tracking** (for special cases where you can't change the base class)
   ```python
   import time
   from django_managed_commands.utils import record_command_execution

   class Command(BaseCommand):
       def handle(self, *args, **options):
           start_time = time.time()
           try:
               # Your logic
               record_command_execution(
                   command_name="myapp.existing_command",
                   success=True,
                   duration=time.time() - start_time,
               )
           except Exception as e:
               record_command_execution(
                   command_name="myapp.existing_command",
                   success=False,
                   error_message=str(e),
                   duration=time.time() - start_time,
               )
               raise
   ```

## API Reference

### Base Classes

#### `ManagedCommand`

Base class for Django management commands with automatic tracking and transaction support.

**Location:** `django_managed_commands.base.ManagedCommand`

**Class Attributes:**

- `run_once` (bool, default=False): Set to `True` to prevent duplicate executions
- `command_name` (str, default=None): Override to customize the command name. If not set, auto-derived from module path (e.g., `myapp.management.commands.foo` → `myapp.foo`)

**Methods to Override:**

- `execute_command(self, *args, **options)`: Your command logic. Runs inside a database transaction.
- `add_arguments(self, parser)`: Add command-line arguments (same as `BaseCommand`)

**Example:**
```python
from django_managed_commands.base import ManagedCommand


class Command(ManagedCommand):
    help = "Import data from external API"
    run_once = False

    def add_arguments(self, parser):
        parser.add_argument("--source", type=str, required=True)
        parser.add_argument("--dry-run", action="store_true")

    def execute_command(self, *args, **options):
        source = options["source"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write("Dry run mode - no changes will be made")
            return

        # Your logic here - runs in a transaction
        count = self.import_data(source)
        self.stdout.write(self.style.SUCCESS(f"Imported {count} records"))
        return count  # Stored in execution record

    def import_data(self, source):
        # Implementation
        return 42
```

**Behavior:**
- `execute_command()` runs inside `transaction.atomic()`
- Execution is recorded in `CommandExecution` model (success or failure)
- Duration is automatically measured
- On exception: transaction rolls back, error is recorded, exception re-raised

### Utility Functions

#### `record_command_execution()`

Records a command execution in the database.

**Signature:**
```python
record_command_execution(
    command_name,
    success=True,
    parameters=None,
    output="",
    error_message="",
    duration=None,
    run_once=False
)
```

**Parameters:**

- `command_name` (str, required): Unique identifier for the command (e.g., `'myapp.my_command'`)
- `success` (bool, optional): Whether the command executed successfully. Default: `True`
- `parameters` (dict, optional): Dictionary of command arguments and options. Default: `None`
- `output` (str, optional): Standard output from the command. Default: `""`
- `error_message` (str, optional): Error message if the command failed. Default: `""`
- `duration` (float, optional): Execution duration in seconds. Default: `None`
- `run_once` (bool, optional): Whether this command should only run once. Default: `False`

**Returns:** `CommandExecution` instance

**Example:**
```python
from django_managed_commands.utils import record_command_execution

# Record successful execution
execution = record_command_execution(
    command_name='myapp.send_emails',
    success=True,
    parameters={'recipient': 'user@example.com'},
    output='Sent 5 emails',
    duration=2.5
)

# Record failed execution
execution = record_command_execution(
    command_name='myapp.process_data',
    success=False,
    error_message='Database connection failed',
    duration=0.3
)

# Record run-once command
execution = record_command_execution(
    command_name='myapp.setup_initial_data',
    success=True,
    output='Created 100 records',
    duration=5.2,
    run_once=True
)
```

#### `should_run_command()`

Checks if a command should execute based on its execution history.

**Signature:**
```python
should_run_command(command_name)
```

**Parameters:**

- `command_name` (str, required): The name of the command to check

**Returns:** `bool` - `True` if the command should run, `False` if it should be skipped

**Behavior:**

- Returns `True` if no previous execution exists
- Returns `True` if the most recent execution failed
- Returns `True` if the most recent execution had `run_once=False`
- Returns `False` only if the most recent execution was successful AND had `run_once=True`

**Example:**
```python
from django_managed_commands.utils import should_run_command, record_command_execution

# First time running
if should_run_command('myapp.setup_data'):
    # Returns True - no previous execution
    setup_data()
    record_command_execution('myapp.setup_data', success=True, run_once=True)

# Second time running
if should_run_command('myapp.setup_data'):
    # Returns False - already run successfully with run_once=True
    setup_data()
else:
    print('Command already executed successfully')

# After a failed execution
record_command_execution('myapp.setup_data', success=False, run_once=True)
if should_run_command('myapp.setup_data'):
    # Returns True - previous execution failed, so retry is allowed
    setup_data()
```

#### `get_command_history()`

Retrieves execution history for a specific command.

**Signature:**
```python
get_command_history(command_name, limit=10)
```

**Parameters:**

- `command_name` (str, required): The name of the command to retrieve history for
- `limit` (int, optional): Maximum number of records to return. Default: `10`

**Returns:** `QuerySet` of `CommandExecution` instances, ordered by execution time (newest first)

**Example:**
```python
from django_managed_commands.utils import get_command_history

# Get last 10 executions
history = get_command_history('myapp.send_notifications')
for execution in history:
    print(f"{execution.executed_at}: {execution.success}")

# Get last 5 executions
recent = get_command_history('myapp.process_data', limit=5)
print(f"Found {recent.count()} executions")

# Check if command has ever run
history = get_command_history('myapp.new_command', limit=1)
if history.exists():
    print(f"Last run: {history.first().executed_at}")
else:
    print("Command has never been executed")

# Analyze execution patterns
history = get_command_history('myapp.daily_task', limit=30)
success_rate = history.filter(success=True).count() / history.count() * 100
print(f"Success rate: {success_rate:.1f}%")
```

### Management Commands

#### `create_managed_command`

Generates a new Django management command with built-in execution tracking.

**Usage:**
```bash
python manage.py create_managed_command <app_name> <command_name> [options]
```

**Arguments:**

- `app_name` (required): Name of the Django app (must be in `INSTALLED_APPS`)
- `command_name` (required): Name of the command to create (must be a valid Python identifier)

**Options:**

- `--run-once`: Set `run_once=True` in the generated command to prevent duplicate executions
- `--force`: Overwrite existing files if they exist

**Example:**
```bash
# Create a standard command
python manage.py create_managed_command myapp send_notifications

# Create a run-once command
python manage.py create_managed_command myapp setup_initial_data --run-once

# Overwrite existing command
python manage.py create_managed_command myapp existing_command --force
```

**Generated Files:**

1. Command file: `<app_name>/management/commands/<command_name>.py`
2. Test file: `<app_name>/tests/test_<command_name>.py`

### Models

#### `CommandExecution`

Tracks execution history of Django management commands.

**Fields:**

- `command_name` (CharField, max_length=255): Name of the management command
- `executed_at` (DateTimeField, auto_now_add=True): Timestamp when command was executed
- `success` (BooleanField, default=True): Whether the command completed successfully
- `parameters` (JSONField, null=True, blank=True): Command parameters as JSON
- `output` (TextField, blank=True): Command stdout output
- `error_message` (TextField, blank=True): Error message if command failed
- `duration` (FloatField, null=True, blank=True): Execution duration in seconds
- `run_once` (BooleanField, default=False): Whether this command should only run once

**Meta Options:**

- Ordering: `["-executed_at"]` (newest first)
- Verbose name: "Command Execution"
- Verbose name plural: "Command Executions"

**Methods:**

- `__str__()`: Returns `"{command_name} - {Success|Failed}"`

**Example Usage:**
```python
from django_managed_commands.models import CommandExecution
from django.utils import timezone
from datetime import timedelta

# Query all executions
all_executions = CommandExecution.objects.all()

# Filter by command name
send_email_history = CommandExecution.objects.filter(
    command_name='myapp.send_emails'
)

# Filter by success status
failed_commands = CommandExecution.objects.filter(success=False)

# Get recent executions (last 24 hours)
recent = CommandExecution.objects.filter(
    executed_at__gte=timezone.now() - timedelta(days=1)
)

# Get commands that took longer than 10 seconds
slow_commands = CommandExecution.objects.filter(
    duration__gt=10.0
)

# Get run-once commands
one_time_commands = CommandExecution.objects.filter(run_once=True)

# Aggregate statistics
from django.db.models import Avg, Max, Min, Count

stats = CommandExecution.objects.aggregate(
    total=Count('id'),
    avg_duration=Avg('duration'),
    max_duration=Max('duration'),
    min_duration=Min('duration')
)
```

## Contributing

Contributions are welcome! Report bugs or request features via [GitHub Issues](https://github.com/sbenemerito/django-managed-commands/issues) 🙏

1. **Fork the repository** and create a new branch for your feature or bugfix
2. **Write tests** for any new functionality
3. **Follow code style**: Ensure your code follows PEP 8 and Django best practices. Use [ruff](https://github.com/astral-sh/ruff) for linting. 
4. **Update documentation**: Add or update relevant documentation for your changes
5. **Submit a pull request**: Provide a clear description of your changes

*Note: Yes, I'm currently pushing directly to main - I know, I know. When contributors come around, I'll enforce proper branch protection and PR workflows 🙇‍♂️*

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/django-managed-commands.git
cd django-managed-commands

# Run tests
uv run pytest -v
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
