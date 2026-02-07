"""
Models for tracking Django management command execution.

This module provides the CommandExecution model which tracks when management
commands are run, their parameters, output, and execution status.
"""
from django.db import models


class CommandExecution(models.Model):
    """
    Tracks execution history of Django management commands.
    
    This model stores information about each time a management command is run,
    including its parameters, output, success status, and duration. It provides
    an audit trail for command execution and helps prevent duplicate runs of
    commands that should only execute once.
    """
    
    command_name = models.CharField(
        max_length=255,
        help_text="Name of the management command"
    )
    executed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when command was executed"
    )
    success = models.BooleanField(
        default=True,
        help_text="Whether the command completed successfully"
    )
    parameters = models.JSONField(
        null=True,
        blank=True,
        help_text="Command parameters as JSON"
    )
    output = models.TextField(
        blank=True,
        default="",
        help_text="Command stdout output"
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if command failed"
    )
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="How long the command took to run (in seconds)"
    )
    run_once = models.BooleanField(
        default=False,
        help_text="Whether this command should only run once"
    )
    
    def __str__(self):
        """Return string representation of command execution."""
        status = "Success" if self.success else "Failed"
        return f"{self.command_name} - {status}"
    

    
    class Meta:
        """Meta options for CommandExecution model."""
        ordering = ["-executed_at"]
        verbose_name = "Command Execution"
        verbose_name_plural = "Command Executions"
