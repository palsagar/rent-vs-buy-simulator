---
name: docstring-numpy
description: Convert all Python docstrings to NumPy style with RST examples. Systematically processes files in a user-defined scope, enforcing consistent docstring format.
---

# NumPy Docstring Standardizer

Convert Python docstrings to NumPy style and ensure each has an RST example block.

## When to Use

- User asks to standardize, fix, or convert docstrings
- User mentions "numpy style", "docstring format", or "RST examples"
- User wants consistent documentation across Python files
- Preparing code for Sphinx documentation generation

## Instructions

### 1. Clarify Scope

Ask the user:
- **Scope**: Which files or directories to process?
- **Public only?**: Process all functions or just public API? (default: all)

If unclear, ask before proceeding.

### 2. Discover Files

Find Python files in scope:

```bash
find /path/to/scope -name "*.py" -type f
```

Report file count and confirm before proceeding.

### 3. Process Each File

For each Python file:

1. Read the file
2. Identify all docstrings (module, class, method, function)
3. Convert each to NumPy style
4. Add RST example if missing
5. Write changes back

### 4. NumPy Docstring Format

Every docstring must follow this structure:

```python
def function_name(param1, param2):
    """Short one-line summary.

    Extended description if needed. Can span multiple lines.

    Parameters
    ----------
    param1 : type
        Description of param1.
    param2 : type, optional
        Description of param2. Default is X.

    Returns
    -------
    type
        Description of return value.

    Raises
    ------
    ExceptionType
        When this exception is raised.

    Examples
    --------
    Basic usage example:

    .. code-block:: python

        from module import function_name
        result = function_name("value", 42)

    """
```

### 5. Section Order

Use this exact order (include only relevant sections):

1. **Summary** - Single line, imperative mood ("Return" not "Returns")
2. **Extended Summary** - Optional, after blank line
3. **Parameters** - Function/method inputs
4. **Returns** / **Yields** - What is returned
5. **Raises** - Exceptions that may be raised
6. **See Also** - Related functions/classes
7. **Notes** - Implementation notes (RST allowed)
8. **References** - Citations
9. **Examples** - **Required** - RST code-block format

### 6. Example Block Requirements

Every docstring **must** have an `Examples` section:

```python
Examples
--------
Basic usage:

.. code-block:: python

    from entalmat.bulk import BulkStructure
    structure = BulkStructure.from_file("POSCAR")
    volume = structure.get_volume()

```

Rules:
- Use `.. code-block:: python` directive for code examples
- Add descriptive text before each code block ("Basic usage:", "Create with custom settings:", etc.)
- Indent code 4 spaces after the directive
- No need to show output (unless demonstrating expected results)
- Keep examples minimal but functional
- Import what you use
- Multiple examples can be shown with separate descriptive headers

### 7. Common Conversions

#### Google → NumPy

**Before (Google):**
```python
def func(x):
    """Summary.

    Args:
        x (int): Description.

    Returns:
        str: Description.
    """
```

**After (NumPy):**
```python
def func(x):
    """Summary.

    Parameters
    ----------
    x : int
        Description.

    Returns
    -------
    str
        Description.

    Examples
    --------
    Basic usage:

    .. code-block:: python

        result = func(5)

    """
```

#### Sphinx → NumPy

**Before (Sphinx/reST):**
```python
def func(x):
    """Summary.

    :param x: Description.
    :type x: int
    :returns: Description.
    :rtype: str
    """
```

**After (NumPy):**
```python
def func(x):
    """Summary.

    Parameters
    ----------
    x : int
        Description.

    Returns
    -------
    str
        Description.

    Examples
    --------
    Basic usage:

    .. code-block:: python

        result = func(5)

    """
```

### 8. Type Annotation Handling

If type hints exist in signature, still include types in docstring for clarity:

```python
def func(x: int) -> str:
    """Summary.

    Parameters
    ----------
    x : int
        Description.

    Returns
    -------
    str
        Description.

    Examples
    --------
    Basic usage:

    .. code-block:: python

        result = func(5)

    """
```

### 9. Class Docstrings

```python
class MyClass:
    """Short summary.

    Extended description.

    Parameters
    ----------
    param1 : type
        Description.

    Attributes
    ----------
    attr1 : type
        Description of instance attribute.

    Examples
    --------
    Create an instance:

    .. code-block:: python

        obj = MyClass("value")
        print(obj.attr1)

    """
```

### 10. Edge Cases

- **Private functions** (`_func`): Include docstrings but examples optional
- **Dunder methods** (`__init__`): Document parameters, examples optional
- **Properties**: Treat like attributes, use `Returns` section
- **Abstract methods**: Document interface, example can show subclass usage
- **Generators**: Use `Yields` instead of `Returns`

### 11. Verification

After processing, verify with:

```bash
# Check docstring coverage (if pydocstyle installed)
pydocstyle --convention=numpy /path/to/scope

# Or check with ruff
ruff check --select=D /path/to/scope
```

### 12. Summary Report

Provide:
- Files processed
- Docstrings converted
- Examples added
- Any docstrings skipped and why
