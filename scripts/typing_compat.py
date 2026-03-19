"""
Typing compatibility shim for Python < 3.11.

This module backports typing features from typing_extensions to the typing module
for older Python versions. Must be imported before any modules that use these features.
"""
import sys

# Only apply patches for Python < 3.11
if sys.version_info < (3, 11):
    try:
        import typing
        from typing_extensions import Self, Never, LiteralString, TypeVarTuple, Unpack
        
        # Monkey-patch typing module to include backported features
        if not hasattr(typing, 'Self'):
            typing.Self = Self
        if not hasattr(typing, 'Never'):
            typing.Never = Never
        if not hasattr(typing, 'LiteralString'):
            typing.LiteralString = LiteralString
        if not hasattr(typing, 'TypeVarTuple'):
            typing.TypeVarTuple = TypeVarTuple
        if not hasattr(typing, 'Unpack'):
            typing.Unpack = Unpack
            
    except ImportError:
        # typing_extensions not installed, warn but don't crash
        pass
