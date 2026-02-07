"""Utility functions for django_managed_commands."""

from .models import CommandExecution


def record_command_execution(
    command_name,
    success=True,
    parameters=None,
    output="",
    error_message="",
    duration=None,
    run_once=False,
):
    """
    Record a command execution in the database.

    Creates and saves a CommandExecution instance with the provided parameters.
    This function is used to track when management commands are executed,
    their success status, and any relevant metadata.

    Args:
        command_name (str): The name of the management command that was executed.
        success (bool, optional): Whether the command executed successfully. Defaults to True.
        parameters (dict, optional): Dictionary of parameters passed to the command. Defaults to None.
        output (str, optional): Standard output from the command execution. Defaults to "".
        error_message (str, optional): Error message if the command failed. Defaults to "".
        duration (float, optional): Execution duration in seconds. Defaults to None.
        run_once (bool, optional): Whether this command should only run once. Defaults to False.

    Returns:
        CommandExecution: The created and saved CommandExecution instance.

    Example:
        >>> result = record_command_execution(
        ...     command_name="migrate",
        ...     success=True,
        ...     parameters={"app": "myapp"},
        ...     output="Applied 3 migrations",
        ...     duration=2.5
        ... )
        >>> print(result.command_name)
        migrate
    """
    execution = CommandExecution.objects.create(
        command_name=command_name,
        success=success,
        parameters=parameters,
        output=output,
        error_message=error_message,
        duration=duration,
        run_once=run_once,
    )
    return execution


def should_run_command(command_name):
    """
    Check if a command should be executed based on its execution history.

    Determines whether a command should run by checking if it has been
    successfully executed before with run_once=True. This is useful for
    commands that should only execute once (e.g., data migrations, one-time setup).

    Args:
        command_name (str): The name of the management command to check.

    Returns:
        bool: True if the command should run, False if it should be skipped.
              Returns False only if the most recent execution was successful
              and had run_once=True. Returns True in all other cases:
              - No previous execution exists
              - Previous execution failed (success=False)
              - Previous execution had run_once=False

    Example:
        >>> # First time running a command
        >>> should_run_command("setup_initial_data")
        True
        >>> # After successful run_once execution
        >>> record_command_execution("setup_initial_data", success=True, run_once=True)
        >>> should_run_command("setup_initial_data")
        False
        >>> # After failed run_once execution
        >>> record_command_execution("setup_initial_data", success=False, run_once=True)
        >>> should_run_command("setup_initial_data")
        True
    """
    most_recent = (
        CommandExecution.objects.filter(command_name=command_name)
        .order_by("-executed_at")
        .first()
    )

    if most_recent is None:
        return True

    # Only skip if the most recent execution was successful AND run_once=True
    if most_recent.run_once and most_recent.success:
        return False

    return True


def get_command_history(command_name, limit=10):
    """
    Retrieve the execution history for a specific command.

    Returns a QuerySet of CommandExecution records for the specified command,
    ordered by execution time (newest first) and limited to the specified number
    of results.

    Args:
        command_name (str): The name of the management command to retrieve history for.
        limit (int, optional): Maximum number of records to return. Defaults to 10.

    Returns:
        QuerySet: A Django QuerySet of CommandExecution instances, ordered by
                  -executed_at (newest first), limited to the specified count.

    Example:
        >>> # Get the last 5 executions of a command
        >>> history = get_command_history("migrate", limit=5)
        >>> for execution in history:
        ...     print(f"{execution.executed_at}: {execution.success}")
        2024-01-15 10:30:00: True
        2024-01-14 09:15:00: True
        2024-01-13 08:00:00: False

        >>> # Get default 10 most recent executions
        >>> recent = get_command_history("collectstatic")
        >>> print(recent.count())
        10
    """
    return (
        CommandExecution.objects.filter(command_name=command_name)
        .order_by("-executed_at")
        .all()[:limit]
    )
