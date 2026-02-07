"""
Django admin configuration for django_managed_commands.

This module registers the CommandExecution model with the Django admin interface,
providing a read-only view of command execution history with filtering and search
capabilities.
"""
from django.contrib import admin

from .models import CommandExecution


@admin.register(CommandExecution)
class CommandExecutionAdmin(admin.ModelAdmin):
    """
    Admin interface for CommandExecution model.
    
    Provides a read-only view of command execution history with:
    - List display of key execution details
    - Filtering by success status, command name, and execution date
    - Search by command name, output, and error messages
    - Date hierarchy for easy navigation by execution date
    - All fields read-only to prevent modification of execution records
    """
    
    list_display = ['command_name', 'executed_at', 'success', 'duration']
    list_filter = ['success', 'command_name', 'executed_at', 'run_once']
    search_fields = ['command_name', 'output', 'error_message']
    readonly_fields = [
        'command_name',
        'executed_at',
        'success',
        'parameters',
        'output',
        'error_message',
        'duration',
        'run_once'
    ]
    ordering = ['-executed_at']
    date_hierarchy = 'executed_at'
