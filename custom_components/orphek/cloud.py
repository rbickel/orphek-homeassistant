"""Unused Tuya cloud client removed.

This integration does not currently wire a Tuya IoT cloud client into its
runtime. The previous implementation in this module used synchronous
``requests`` calls and was not referenced anywhere in the integration, so it
has been removed to avoid shipping dead, blocking network code.
"""
