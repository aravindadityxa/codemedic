"""SQLite knowledge base for error explanations, patterns, and fix history."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

from .config import Config

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS errors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_type   TEXT    NOT NULL UNIQUE,
    description      TEXT    NOT NULL DEFAULT '',
    why_it_happens   TEXT    NOT NULL DEFAULT '',
    common_causes    TEXT    NOT NULL DEFAULT '',
    simple_explanation TEXT  NOT NULL DEFAULT '',
    analogy          TEXT    NOT NULL DEFAULT '',
    fixes            TEXT    NOT NULL DEFAULT '',
    example_before   TEXT    NOT NULL DEFAULT '',
    example_after    TEXT    NOT NULL DEFAULT '',
    difficulty       INTEGER NOT NULL DEFAULT 1,
    category         TEXT    NOT NULL DEFAULT 'general',
    docs_url         TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS patterns (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_type   TEXT NOT NULL,
    pattern          TEXT NOT NULL,
    suggestion       TEXT NOT NULL DEFAULT '',
    UNIQUE(exception_type, pattern)
);

CREATE TABLE IF NOT EXISTS fix_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP,
    exception_type   TEXT,
    original_code    TEXT,
    fixed_code       TEXT,
    feedback         INTEGER DEFAULT 0
);
"""

_DEFAULT_ERRORS: list[tuple[Any, ...]] = [
    (
        "ArithmeticError",
        "Base class for numeric computation errors.",
        "Raised when an arithmetic operation fails – e.g. overflow or division by zero.",
        "Performing a numeric operation that has no valid result.",
        "Python detected an impossible arithmetic operation.",
        "Think of it as asking a calculator to do something mathematically undefined.",
        "Catch it with 'except ArithmeticError' or handle the specific subclass.",
        "result = 1 / 0",
        "result = 1 / divisor if divisor != 0 else 0",
        1, "arithmetic",
        "https://docs.python.org/3/library/exceptions.html#ArithmeticError",
    ),
    (
        "AssertionError",
        "Raised when an 'assert' statement fails.",
        "The condition in an assert statement evaluated to False.",
        "assert False  # or assert some_condition that is False",
        "Your code hit an 'assert' whose condition was False.",
        "It's like a promise that was broken – the guarantee you wrote in code didn't hold.",
        "Fix the logic so the assertion holds, or handle with try/except AssertionError.",
        "assert len(items) > 0",
        "if not items:\n    raise ValueError('items must not be empty')",
        1, "assertion",
        "https://docs.python.org/3/library/exceptions.html#AssertionError",
    ),
    (
        "AttributeError",
        "Object does not have the requested attribute or method.",
        "You accessed an attribute or called a method that does not exist on the object.",
        "Misspelled attribute name; wrong object type; method not defined.",
        "You tried to use something the object doesn't have – like asking a bicycle to fly.",
        "It's like calling a feature on a phone that model doesn't support.",
        "Check spelling; use dir(obj) to inspect available attributes.",
        "x = 5\nx.append(3)",
        "x = [5]\nx.append(3)",
        1, "attribute",
        "https://docs.python.org/3/library/exceptions.html#AttributeError",
    ),
    (
        "BlockingIOError",
        "Raised when a non-blocking I/O operation is blocked.",
        "A non-blocking socket or file descriptor would block on the attempted operation.",
        "Using non-blocking I/O without handling EAGAIN/EWOULDBLOCK.",
        "The I/O resource is busy and would block.",
        "Like trying to enter a revolving door that's already spinning.",
        "Use asyncio, select, or retry the operation after a short delay.",
        "sock.setblocking(False)\nsock.recv(1024)",
        "import select\nready = select.select([sock], [], [], timeout=1.0)",
        3, "io",
        "https://docs.python.org/3/library/exceptions.html#BlockingIOError",
    ),
    (
        "BrokenPipeError",
        "Raised when writing to a pipe whose read end is closed.",
        "The other end of a pipe or socket was closed before you finished writing.",
        "Writing to stdout when the consumer has exited; closed network connection.",
        "You're writing data but nobody is listening on the other end.",
        "Like shouting into a phone after the other person hung up.",
        "Handle with try/except BrokenPipeError; check if the connection is still open.",
        "import sys\nfor line in data:\n    sys.stdout.write(line)",
        "try:\n    for line in data:\n        sys.stdout.write(line)\nexcept BrokenPipeError:\n    pass",
        2, "io",
        "https://docs.python.org/3/library/exceptions.html#BrokenPipeError",
    ),
    (
        "BufferError",
        "Raised when a buffer-related operation cannot be completed.",
        "A buffer operation (e.g. on memoryview) could not be performed.",
        "Attempting to modify a read-only buffer or release a locked buffer.",
        "The buffer is in a state that doesn't allow the operation.",
        "Like trying to write on a sealed envelope.",
        "Ensure the buffer is writeable and not locked before modifying it.",
        "mv = memoryview(bytes(b'read-only'))\nmv[0] = 65",
        "data = bytearray(b'writable')\nmv = memoryview(data)\nmv[0] = 65",
        3, "buffer",
        "https://docs.python.org/3/library/exceptions.html#BufferError",
    ),
    (
        "ChildProcessError",
        "Raised when a child process operation fails.",
        "An operation on a child process (e.g. wait()) encountered an error.",
        "Child process already terminated; permission issues.",
        "The child process you were managing had a problem.",
        "Like trying to give instructions to a worker who already went home.",
        "Check subprocess return codes and handle os.error conditions.",
        "os.waitpid(pid, 0)",
        "try:\n    os.waitpid(pid, 0)\nexcept ChildProcessError:\n    pass",
        3, "process",
        "https://docs.python.org/3/library/exceptions.html#ChildProcessError",
    ),
    (
        "ConnectionAbortedError",
        "Connection attempt aborted by the network or remote host.",
        "The connection was forcibly closed by the remote host during setup.",
        "Firewall interruption; remote server reset the connection.",
        "The remote side slammed the door before you could walk in.",
        "Like having a phone call cut off right when the other person answered.",
        "Implement retry logic with exponential back-off.",
        "sock.connect((host, port))",
        "for attempt in range(3):\n    try:\n        sock.connect((host, port))\n        break\n    except ConnectionAbortedError:\n        time.sleep(2 ** attempt)",
        3, "network",
        "https://docs.python.org/3/library/exceptions.html#ConnectionAbortedError",
    ),
    (
        "ConnectionError",
        "Base class for connection-related errors.",
        "A network connection could not be established or was interrupted.",
        "Server down; wrong host/port; network unavailable.",
        "Something went wrong with a network connection.",
        "Like trying to call a number that's out of service.",
        "Verify host, port, and network availability; add retry logic.",
        "sock.connect(('invalid.host', 80))",
        "try:\n    sock.connect((host, port))\nexcept ConnectionError as e:\n    print(f'Connection failed: {e}')",
        2, "network",
        "https://docs.python.org/3/library/exceptions.html#ConnectionError",
    ),
    (
        "ConnectionRefusedError",
        "Connection was actively refused by the target host.",
        "No service is listening on the target port.",
        "Service not started; wrong port number.",
        "You knocked on a door and nobody answered – the service is not running.",
        "Like calling a restaurant that's closed.",
        "Make sure the server is running and listening on the correct port.",
        "sock.connect(('localhost', 9999))",
        "# Start the server first, then connect\nsock.connect(('localhost', 9999))",
        2, "network",
        "https://docs.python.org/3/library/exceptions.html#ConnectionRefusedError",
    ),
    (
        "ConnectionResetError",
        "Connection was reset by the remote host.",
        "The remote end closed the connection unexpectedly.",
        "Timeout; server crash; keep-alive failure.",
        "The other side unexpectedly hung up.",
        "Like someone slamming the phone down mid-conversation.",
        "Handle gracefully and reconnect if appropriate.",
        "data = sock.recv(4096)",
        "try:\n    data = sock.recv(4096)\nexcept ConnectionResetError:\n    reconnect()",
        2, "network",
        "https://docs.python.org/3/library/exceptions.html#ConnectionResetError",
    ),
    (
        "EOFError",
        "Raised when input() hits end-of-file with no data.",
        "input() or read() reached the end of the input stream.",
        "Running a script non-interactively that calls input(); piping stdin.",
        "Python tried to read more input but the stream ended.",
        "Like asking someone a question but they've already left the room.",
        "Use try/except EOFError around input(); check your data source.",
        "value = input('Enter a number: ')",
        "try:\n    value = input('Enter a number: ')\nexcept EOFError:\n    value = '0'",
        1, "io",
        "https://docs.python.org/3/library/exceptions.html#EOFError",
    ),
    (
        "FileExistsError",
        "Raised when trying to create a file or directory that already exists.",
        "The target path already exists and the operation requires it not to.",
        "Creating a file with 'x' mode when it already exists; mkdir without exist_ok.",
        "You tried to create something that's already there.",
        "Like trying to register a username that's already taken.",
        "Use exist_ok=True for directories; use 'w' mode instead of 'x' for files.",
        "Path('output').mkdir()",
        "Path('output').mkdir(exist_ok=True)",
        1, "filesystem",
        "https://docs.python.org/3/library/exceptions.html#FileExistsError",
    ),
    (
        "FileNotFoundError",
        "File or directory does not exist at the given path.",
        "The path you provided does not point to an existing file or directory.",
        "Typo in path; wrong working directory; file deleted.",
        "You tried to open a file that doesn't exist – double-check the path.",
        "Like trying to read a book that's not on the shelf.",
        "Verify the path with Path.exists(); use try/except FileNotFoundError.",
        "open('data.csv')",
        "from pathlib import Path\nif Path('data.csv').exists():\n    open('data.csv')",
        1, "filesystem",
        "https://docs.python.org/3/library/exceptions.html#FileNotFoundError",
    ),
    (
        "FloatingPointError",
        "Raised when a floating-point operation fails (rarely seen).",
        "A floating-point operation encountered an exceptional condition.",
        "Only raised when FP exceptions are enabled via fpectl.",
        "An unusual floating-point error occurred.",
        "Like a calculator showing 'ERR' for an impossible operation.",
        "Use the 'math' module and handle inf/nan values explicitly.",
        "import math\nmath.sqrt(-1)",
        "import cmath\nresult = cmath.sqrt(-1)  # returns complex number",
        3, "arithmetic",
        "https://docs.python.org/3/library/exceptions.html#FloatingPointError",
    ),
    (
        "GeneratorExit",
        "Raised inside a generator when it is closed.",
        "The generator's close() method was called.",
        "Garbage collection of generator; explicit .close() call.",
        "The generator was shut down before it finished.",
        "Like a factory being closed before it finishes production.",
        "Use try/finally in generators to clean up resources.",
        "def gen():\n    yield 1\n    yield 2\ng = gen()\nnext(g)\ng.close()",
        "def gen():\n    try:\n        yield 1\n        yield 2\n    finally:\n        pass  # cleanup here",
        2, "generator",
        "https://docs.python.org/3/library/exceptions.html#GeneratorExit",
    ),
    (
        "ImportError",
        "Module could not be imported.",
        "Python could not find or load the requested module.",
        "Module not installed; typo in module name; circular imports.",
        "Python tried to import something it couldn't find or load.",
        "Like trying to borrow a book the library doesn't own.",
        "pip install the package; check for typos; avoid circular imports.",
        "import numppy",
        "import numpy",
        1, "import",
        "https://docs.python.org/3/library/exceptions.html#ImportError",
    ),
    (
        "IndentationError",
        "Incorrect indentation in Python code.",
        "The indentation of a line is inconsistent with surrounding code.",
        "Mixing tabs and spaces; forgetting to indent after a colon.",
        "Python cares deeply about whitespace – your indentation is off.",
        "Like a sentence starting in the middle of a page for no reason.",
        "Use consistent spaces (4 per level) and never mix tabs with spaces.",
        "if True:\nprint('hello')",
        "if True:\n    print('hello')",
        1, "syntax",
        "https://docs.python.org/3/library/exceptions.html#IndentationError",
    ),
    (
        "IndexError",
        "Sequence subscript is out of the valid range.",
        "You tried to access an index that doesn't exist in the list or tuple.",
        "Off-by-one; iterating past the end; empty list access.",
        "You reached for a shelf slot that doesn't exist.",
        "Like asking for the 10th item in a 5-item list.",
        "Check len(seq) before indexing; use enumerate(); use .get() equivalent.",
        "my_list = [1, 2, 3]\nmy_list[5]",
        "my_list = [1, 2, 3]\nif 5 < len(my_list):\n    print(my_list[5])",
        1, "sequence",
        "https://docs.python.org/3/library/exceptions.html#IndexError",
    ),
    (
        "InterruptedError",
        "System call interrupted by a signal.",
        "A low-level system call was interrupted by an OS signal.",
        "SIGINT (Ctrl-C) or other signal arriving during a blocking call.",
        "The OS interrupted what Python was doing.",
        "Like a fire alarm going off mid-meeting.",
        "Python 3.5+ retries interrupted syscalls automatically; catch if needed.",
        "time.sleep(100)  # interrupted by signal",
        "try:\n    time.sleep(100)\nexcept InterruptedError:\n    pass",
        3, "os",
        "https://docs.python.org/3/library/exceptions.html#InterruptedError",
    ),
    (
        "IsADirectoryError",
        "A file operation was attempted on a directory.",
        "You tried to perform a file operation on a path that is a directory.",
        "Passing a directory path to open(); trying to read a folder as a file.",
        "You treated a folder like a file.",
        "Like trying to read the contents of a filing cabinet drawer directly.",
        "Check with Path.is_dir() before performing file operations.",
        "open('/tmp')",
        "from pathlib import Path\npath = Path('/tmp')\nif path.is_file():\n    open(path)",
        1, "filesystem",
        "https://docs.python.org/3/library/exceptions.html#IsADirectoryError",
    ),
    (
        "KeyError",
        "Dictionary key does not exist.",
        "You tried to access a key that is not present in the dictionary.",
        "Typo in key name; assuming key exists without checking; case sensitivity.",
        "You asked for something in a dictionary that isn't there.",
        "Like looking up a word in a dictionary that hasn't been added yet.",
        "Use dict.get(key, default); check with 'key in dict'; use collections.defaultdict.",
        "d = {'name': 'Alice'}\nprint(d['age'])",
        "d = {'name': 'Alice'}\nprint(d.get('age', 'unknown'))",
        1, "mapping",
        "https://docs.python.org/3/library/exceptions.html#KeyError",
    ),
    (
        "KeyboardInterrupt",
        "User pressed Ctrl-C to interrupt the program.",
        "The program received a keyboard interrupt signal (SIGINT).",
        "User pressed Ctrl-C; signal sent programmatically.",
        "The user manually stopped the program.",
        "Like someone pulling the fire alarm to stop a performance.",
        "Catch with try/except KeyboardInterrupt to clean up gracefully.",
        "while True:\n    pass",
        "try:\n    while True:\n        pass\nexcept KeyboardInterrupt:\n    print('Stopped by user')",
        1, "signal",
        "https://docs.python.org/3/library/exceptions.html#KeyboardInterrupt",
    ),
    (
        "LookupError",
        "Base class for index/key lookup errors.",
        "A key or index lookup operation failed.",
        "Parent of IndexError and KeyError.",
        "You tried to find something using an index or key and it wasn't there.",
        "Like searching a catalogue for an item that's out of stock.",
        "Use the specific subclass (IndexError, KeyError) for targeted handling.",
        "my_list[99]",
        "try:\n    val = my_list[99]\nexcept LookupError:\n    val = None",
        1, "lookup",
        "https://docs.python.org/3/library/exceptions.html#LookupError",
    ),
    (
        "MemoryError",
        "Program ran out of available memory.",
        "Python could not allocate enough memory for an operation.",
        "Creating very large data structures; memory leak; insufficient RAM.",
        "Your program asked for more memory than the system could provide.",
        "Like trying to pour a swimming pool into a bucket.",
        "Process data in chunks; release references; use generators instead of lists.",
        "data = [0] * 10**10",
        "# Use a generator\ndata = (0 for _ in range(10**10))",
        2, "memory",
        "https://docs.python.org/3/library/exceptions.html#MemoryError",
    ),
    (
        "ModuleNotFoundError",
        "The requested module could not be found.",
        "Python searched sys.path and could not locate the module.",
        "Package not installed; wrong virtual environment; typo in name.",
        "The module you tried to import doesn't exist in your environment.",
        "Like ordering food from a restaurant not in your delivery area.",
        "Run 'pip install <package>'; check your virtual environment is active.",
        "import pandas",
        "# First: pip install pandas\nimport pandas",
        1, "import",
        "https://docs.python.org/3/library/exceptions.html#ModuleNotFoundError",
    ),
    (
        "NameError",
        "A local or global name is not defined.",
        "Python encountered a name it has never seen or that is out of scope.",
        "Misspelled variable name; variable used before assignment; wrong scope.",
        "You used a name Python doesn't know about – check spelling and scope.",
        "Like calling out to a friend who isn't in the room.",
        "Check spelling; define the variable before using it; check scope.",
        "print(messge)",
        "message = 'Hello'\nprint(message)",
        1, "name",
        "https://docs.python.org/3/library/exceptions.html#NameError",
    ),
    (
        "NotADirectoryError",
        "A directory operation was attempted on a non-directory path.",
        "An operation expecting a directory was given a file path.",
        "Passing a file path to os.listdir(); using a file as a parent path.",
        "You tried to use a file as if it were a folder.",
        "Like trying to open a book as if it were a filing cabinet.",
        "Check with Path.is_dir() before directory operations.",
        "os.listdir('file.txt')",
        "from pathlib import Path\npath = Path('file.txt')\nif path.is_dir():\n    os.listdir(path)",
        1, "filesystem",
        "https://docs.python.org/3/library/exceptions.html#NotADirectoryError",
    ),
    (
        "NotImplementedError",
        "An abstract method or stub has not been implemented.",
        "A method that should be overridden in a subclass was called on the base class.",
        "Forgetting to implement an abstract method; placeholder method called.",
        "This method exists as a placeholder – someone needs to write it.",
        "Like a menu item listed as 'coming soon'.",
        "Implement the method in the subclass.",
        "class Animal:\n    def speak(self):\n        raise NotImplementedError\n\nAnimal().speak()",
        "class Dog(Animal):\n    def speak(self):\n        return 'Woof!'",
        1, "implementation",
        "https://docs.python.org/3/library/exceptions.html#NotImplementedError",
    ),
    (
        "OSError",
        "Operating system error.",
        "An OS-level operation (file I/O, process, network) failed.",
        "Permissions; disk full; invalid path; resource limits.",
        "The operating system reported an error.",
        "Like the OS filing a complaint about what you asked it to do.",
        "Check errno; use try/except OSError; verify permissions and paths.",
        "open('/root/secret.txt', 'w')",
        "try:\n    open('/root/secret.txt', 'w')\nexcept PermissionError:\n    print('No permission')",
        2, "os",
        "https://docs.python.org/3/library/exceptions.html#OSError",
    ),
    (
        "OverflowError",
        "Arithmetic result is too large to be represented.",
        "A numeric computation produced a value that exceeds the representable range.",
        "Very large integer exponentiation; floating-point overflow.",
        "Your number grew so large Python couldn't hold it.",
        "Like trying to fit a skyscraper into a shoebox.",
        "Use decimal module for precision; check inputs before computing.",
        "import math\nmath.exp(1000)",
        "import math\ntry:\n    result = math.exp(1000)\nexcept OverflowError:\n    result = float('inf')",
        2, "arithmetic",
        "https://docs.python.org/3/library/exceptions.html#OverflowError",
    ),
    (
        "PermissionError",
        "Insufficient permissions to perform the operation.",
        "The OS denied the operation due to file or directory permissions.",
        "Reading a protected file; writing to a read-only path; OS restrictions.",
        "You don't have permission to do that operation.",
        "Like trying to enter a room without the right access badge.",
        "Run with elevated privileges if appropriate; change file permissions.",
        "open('/etc/passwd', 'w')",
        "try:\n    open('/etc/passwd', 'w')\nexcept PermissionError:\n    print('Permission denied')",
        1, "filesystem",
        "https://docs.python.org/3/library/exceptions.html#PermissionError",
    ),
    (
        "ProcessLookupError",
        "Process with the given PID does not exist.",
        "An operation was attempted on a process ID that no longer exists.",
        "Process already terminated; wrong PID.",
        "You tried to interact with a process that no longer exists.",
        "Like trying to call someone who has already left the building.",
        "Check if the process is still running before sending signals.",
        "os.kill(pid, signal.SIGTERM)",
        "try:\n    os.kill(pid, signal.SIGTERM)\nexcept ProcessLookupError:\n    pass",
        3, "process",
        "https://docs.python.org/3/library/exceptions.html#ProcessLookupError",
    ),
    (
        "RecursionError",
        "Maximum recursion depth exceeded.",
        "A recursive function called itself too many times without a base case.",
        "Missing or unreachable base case; infinite mutual recursion.",
        "Your function kept calling itself forever (or too deep).",
        "Like two mirrors facing each other – infinite reflections.",
        "Add or fix a base case; consider iterative solution; increase sys.setrecursionlimit cautiously.",
        "def factorial(n):\n    return n * factorial(n - 1)",
        "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
        2, "recursion",
        "https://docs.python.org/3/library/exceptions.html#RecursionError",
    ),
    (
        "ReferenceError",
        "Weak reference target no longer exists.",
        "A weak reference was dereferenced after its target was garbage collected.",
        "Holding a weakref to an object that was collected.",
        "The object you were weakly referencing was cleaned up.",
        "Like keeping a sticky note with someone's address after they moved.",
        "Check if the reference is alive before dereferencing.",
        "import weakref\nref = weakref.ref(obj)\ndel obj\nref()()",
        "import weakref\nref = weakref.ref(obj)\ndel obj\ntarget = ref()\nif target is not None:\n    target()",
        3, "memory",
        "https://docs.python.org/3/library/exceptions.html#ReferenceError",
    ),
    (
        "RuntimeError",
        "Generic runtime error that doesn't fit other categories.",
        "Raised when an error is detected that doesn't belong to any other category.",
        "Thread/async violations; state machine errors; various library errors.",
        "Something went wrong at runtime that doesn't have a more specific name.",
        "Like an 'unexpected error' message on a website.",
        "Read the error message carefully; it describes the specific issue.",
        "raise RuntimeError('Something went wrong')",
        "# Address the specific root cause described in the message",
        2, "runtime",
        "https://docs.python.org/3/library/exceptions.html#RuntimeError",
    ),
    (
        "StopAsyncIteration",
        "Raised to signal the end of an async iterator.",
        "__anext__() raised StopAsyncIteration to signal the iterator is exhausted.",
        "Implementing async iterators incorrectly.",
        "The async iteration is complete.",
        "Like a conveyor belt reaching the end.",
        "Use 'async for' to iterate; the exception is handled automatically.",
        "async def __anext__(self):\n    raise StopAsyncIteration",
        "# Use 'async for item in async_iterable:' instead of manual __anext__",
        3, "async",
        "https://docs.python.org/3/library/exceptions.html#StopAsyncIteration",
    ),
    (
        "StopIteration",
        "Raised to signal the end of an iterator.",
        "__next__() raised StopIteration to signal the iterator is exhausted.",
        "Calling next() on an exhausted iterator without a default.",
        "The iteration is complete – there are no more items.",
        "Like a book reaching its last page.",
        "Use for loops instead of manual next(); provide a default to next().",
        "it = iter([1, 2])\nnext(it)\nnext(it)\nnext(it)  # raises StopIteration",
        "it = iter([1, 2])\nval = next(it, None)  # returns None instead of raising",
        1, "iterator",
        "https://docs.python.org/3/library/exceptions.html#StopIteration",
    ),
    (
        "SyntaxError",
        "Invalid Python syntax.",
        "The Python parser could not understand the code you wrote.",
        "Missing colon after if/for/def; mismatched parentheses; invalid tokens.",
        "Python couldn't understand your code – there's a grammar mistake.",
        "Like writing a sentence without a verb.",
        "Read the caret (^) position; check for missing colons, brackets, quotes.",
        "if x > 0\n    print(x)",
        "if x > 0:\n    print(x)",
        1, "syntax",
        "https://docs.python.org/3/library/exceptions.html#SyntaxError",
    ),
    (
        "SystemError",
        "Internal error in the Python interpreter.",
        "The Python interpreter itself detected an internal inconsistency.",
        "Usually a CPython bug; corrupted extension modules.",
        "Something went wrong inside Python itself (very rare).",
        "Like the factory's own machinery breaking down.",
        "Report to the Python bug tracker; check for corrupted .pyc files.",
        "# Usually triggered by buggy C extensions",
        "# Reinstall packages; report bug to Python or library maintainer",
        3, "internal",
        "https://docs.python.org/3/library/exceptions.html#SystemError",
    ),
    (
        "SystemExit",
        "Raised by sys.exit() to terminate the interpreter.",
        "sys.exit() was called, or the script finished with a non-zero exit code request.",
        "Explicit sys.exit() call; exit() called in scripts.",
        "The program intentionally requested to exit.",
        "Like formally submitting a resignation letter.",
        "Catch with except SystemExit if you need to do cleanup, then re-raise.",
        "sys.exit(1)",
        "try:\n    sys.exit(1)\nexcept SystemExit:\n    cleanup()\n    raise",
        1, "system",
        "https://docs.python.org/3/library/exceptions.html#SystemExit",
    ),
    (
        "TabError",
        "Inconsistent use of tabs and spaces.",
        "Indentation contains both tabs and spaces in an ambiguous way.",
        "Mixing tab and space characters for indentation.",
        "Your code mixes tabs and spaces, which Python can't interpret.",
        "Like writing notes half in pencil and half in ink – confusing to read.",
        "Convert all indentation to 4 spaces; use an editor that shows whitespace.",
        "def foo():\n\t    pass  # tab + spaces",
        "def foo():\n    pass  # 4 spaces only",
        1, "syntax",
        "https://docs.python.org/3/library/exceptions.html#TabError",
    ),
    (
        "TimeoutError",
        "Operation timed out.",
        "A system function timed out waiting for a resource.",
        "Network request too slow; subprocess taking too long; lock acquisition timeout.",
        "The operation took too long and Python gave up waiting.",
        "Like waiting at a restaurant that takes forever – you eventually leave.",
        "Increase timeout; implement retry logic; check network/resource availability.",
        "sock.settimeout(0.001)\nsock.recv(1024)",
        "sock.settimeout(10.0)  # 10 second timeout\ntry:\n    data = sock.recv(1024)\nexcept TimeoutError:\n    pass",
        2, "network",
        "https://docs.python.org/3/library/exceptions.html#TimeoutError",
    ),
    (
        "TypeError",
        "Operation applied to an object of an inappropriate type.",
        "You used an operator or function with arguments of the wrong type.",
        "Concatenating str with int; calling non-callable; wrong argument type.",
        "You tried to mix incompatible types – like adding text to a number.",
        "Like trying to add apples and invoices – they're different things.",
        "Use explicit type conversion: str(), int(), float(); read the function signature.",
        "print('Age: ' + 25)",
        "print('Age: ' + str(25))\n# or: print(f'Age: {25}')",
        1, "type",
        "https://docs.python.org/3/library/exceptions.html#TypeError",
    ),
    (
        "UnboundLocalError",
        "Local variable referenced before assignment.",
        "A variable is referenced before it has been assigned in the local scope.",
        "Using a variable as both local and global without 'global' keyword.",
        "Python treats the variable as local but you haven't assigned it yet.",
        "Like referring to a tool you haven't picked up yet.",
        "Add 'global' or 'nonlocal' declaration; assign before use.",
        "x = 10\ndef foo():\n    print(x)\n    x = 20",
        "x = 10\ndef foo():\n    global x\n    print(x)\n    x = 20",
        2, "name",
        "https://docs.python.org/3/library/exceptions.html#UnboundLocalError",
    ),
    (
        "UnicodeDecodeError",
        "Failed to decode bytes to a Unicode string.",
        "The bytes could not be decoded using the specified encoding.",
        "Reading a file in UTF-8 that contains Latin-1 bytes; binary data treated as text.",
        "Python tried to convert bytes to text but couldn't understand the encoding.",
        "Like trying to read a French novel with only an English dictionary.",
        "Specify the correct encoding; use errors='replace' or 'ignore'.",
        "open('file.txt', encoding='utf-8').read()",
        "open('file.txt', encoding='utf-8', errors='replace').read()",
        2, "unicode",
        "https://docs.python.org/3/library/exceptions.html#UnicodeDecodeError",
    ),
    (
        "UnicodeEncodeError",
        "Failed to encode a Unicode string to bytes.",
        "A character in the string cannot be encoded in the target encoding.",
        "Writing non-ASCII characters to an ASCII stream; wrong encoding for output.",
        "Python tried to convert text to bytes but found a character it couldn't encode.",
        "Like trying to type a Japanese character on a typewriter with only English keys.",
        "Use UTF-8 encoding; specify errors='replace'; normalise the string first.",
        "open('out.txt', 'w', encoding='ascii').write('café')",
        "open('out.txt', 'w', encoding='utf-8').write('café')",
        2, "unicode",
        "https://docs.python.org/3/library/exceptions.html#UnicodeEncodeError",
    ),
    (
        "UnicodeError",
        "Base class for Unicode encoding/decoding errors.",
        "A Unicode operation (encode or decode) failed.",
        "Wrong codec; incompatible characters; binary data in text mode.",
        "Something went wrong with Unicode text conversion.",
        "Like a translation that breaks down mid-sentence.",
        "Always specify explicit encodings; prefer UTF-8.",
        "b'\\xff'.decode('utf-8')",
        "b'\\xff'.decode('utf-8', errors='replace')",
        2, "unicode",
        "https://docs.python.org/3/library/exceptions.html#UnicodeError",
    ),
    (
        "UnicodeTranslateError",
        "Failed to translate a Unicode string.",
        "str.translate() encountered a character it could not map.",
        "Translating characters not present in the translation table.",
        "Python couldn't map a character using the translation table.",
        "Like a translator encountering a word with no equivalent.",
        "Use errors='replace' or extend your translation table.",
        "s = 'café'\ns.translate({ord('é'): None})",
        "# Ensure all characters in the string have mappings in the table",
        3, "unicode",
        "https://docs.python.org/3/library/exceptions.html#UnicodeTranslateError",
    ),
    (
        "ValueError",
        "Operation received an argument of the right type but invalid value.",
        "The value passed is the correct type but outside the acceptable range or format.",
        "int('hello'); math.sqrt(-1); int('') ; invalid enum value.",
        "The type was right but the value was wrong.",
        "Like ordering a pizza with a negative number of toppings – the type is number, but the value makes no sense.",
        "Validate values before passing them; use try/except ValueError.",
        "int('hello')",
        "try:\n    n = int(user_input)\nexcept ValueError:\n    n = 0",
        1, "value",
        "https://docs.python.org/3/library/exceptions.html#ValueError",
    ),
    (
        "ZeroDivisionError",
        "Division or modulo operation with zero as the divisor.",
        "You attempted to divide or compute modulo by zero.",
        "Literal division by zero; variable that becomes zero; loop counter reaching zero.",
        "Dividing by zero is mathematically undefined.",
        "Like trying to split a pizza into zero slices.",
        "Check that the denominator is non-zero before dividing.",
        "result = total / count",
        "result = total / count if count != 0 else 0",
        1, "arithmetic",
        "https://docs.python.org/3/library/exceptions.html#ZeroDivisionError",
    ),
]


class KnowledgeBase:
    """SQLite-backed knowledge base for error explanations, patterns, and history.

    The database is created at *db_path* (default ``~/.codemedic/errors.db``).
    On first use the schema is initialised and all built-in exception records are
    inserted.
    """

    _INSERT_SQL = """
        INSERT OR IGNORE INTO errors (
            exception_type, description, why_it_happens, common_causes,
            simple_explanation, analogy, fixes, example_before, example_after,
            difficulty, category, docs_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = Config().db_path
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._populate_defaults()
        logger.debug("KnowledgeBase ready at %s", self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            for statement in _SCHEMA.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)

    def _populate_defaults(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM errors")
            if cur.fetchone()[0] > 0:
                return
            conn.executemany(self._INSERT_SQL, _DEFAULT_ERRORS)
            logger.info("Populated knowledge base with %d default entries.", len(_DEFAULT_ERRORS))

    def get_error_info(self, exception_type: str) -> Optional[dict[str, Any]]:
        """Return the full knowledge-base entry for *exception_type*, or ``None``."""
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM errors WHERE exception_type = ?", (exception_type,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_errors(self) -> list[dict[str, Any]]:
        """Return every entry in the errors table, sorted by exception type."""
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM errors ORDER BY exception_type")
            return [dict(r) for r in cur.fetchall()]

    def add_error(
        self,
        exception_type: str,
        description: str,
        why_it_happens: str = "",
        common_causes: str = "",
        simple_explanation: str = "",
        analogy: str = "",
        fixes: str = "",
        example_before: str = "",
        example_after: str = "",
        difficulty: int = 1,
        category: str = "general",
        docs_url: str = "",
    ) -> None:
        """Insert or replace an error entry."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO errors
                   (exception_type, description, why_it_happens, common_causes,
                    simple_explanation, analogy, fixes, example_before, example_after,
                    difficulty, category, docs_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (exception_type, description, why_it_happens, common_causes,
                 simple_explanation, analogy, fixes, example_before, example_after,
                 difficulty, category, docs_url),
            )

    def add_pattern(self, exception_type: str, pattern: str, suggestion: str) -> None:
        """Add a pattern-based fix suggestion for *exception_type*."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO patterns (exception_type, pattern, suggestion) VALUES (?, ?, ?)",
                (exception_type, pattern, suggestion),
            )

    def get_patterns(self, exception_type: str) -> list[tuple[str, str]]:
        """Return ``(pattern, suggestion)`` pairs for *exception_type*."""
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT pattern, suggestion FROM patterns WHERE exception_type = ?",
                (exception_type,),
            )
            return [(r["pattern"], r["suggestion"]) for r in cur.fetchall()]

    def log_fix_attempt(
        self,
        exception_type: str,
        original_code: str,
        fixed_code: str,
        feedback: int = 0,
    ) -> None:
        """Record a fix attempt in the history table."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO fix_history (exception_type, original_code, fixed_code, feedback)
                   VALUES (?, ?, ?, ?)""",
                (exception_type, original_code, fixed_code, feedback),
            )

    def get_fix_history(self, exception_type: Optional[str] = None) -> list[dict[str, Any]]:
        """Return fix history records, optionally filtered by exception type."""
        with self._connect() as conn:
            if exception_type:
                cur = conn.execute(
                    "SELECT * FROM fix_history WHERE exception_type = ? ORDER BY timestamp DESC",
                    (exception_type,),
                )
            else:
                cur = conn.execute("SELECT * FROM fix_history ORDER BY timestamp DESC")
            return [dict(r) for r in cur.fetchall()]

    def count_errors(self) -> int:
        """Return total number of error entries in the knowledge base."""
        with self._connect() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM errors")
            return int(cur.fetchone()[0])
