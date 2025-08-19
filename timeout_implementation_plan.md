# Django Shell MCP Server - Timeout Implementation Plan

## Overview
The Django shell MCP server currently accepts a `timeout` parameter in both the `execute` method and the `django_shell` tool, but the timeout is not enforced. This document outlines the implementation plan to add proper timeout functionality.

## Current State Analysis

### Existing Code Structure
1. **`shell.py`**:
   - `execute(code: str, timeout: int | None = None)` - Async wrapper
   - `_execute(code: str, timeout: int | None = None)` - Synchronous implementation
   - Currently uses `sync_to_async` to run synchronous Django ORM operations in a thread pool
   - Timeout parameter is passed but never used

2. **`server.py`**:
   - `django_shell` tool accepts `timeout` parameter
   - Passes timeout to `shell.execute()` but no enforcement happens

### Technical Constraints
- Django ORM operations are synchronous
- We're using `asgiref.sync.sync_to_async` to bridge async/sync contexts
- Need to handle timeouts in a thread-safe manner
- Must preserve existing functionality when timeout is None

## Implementation Strategy

### 1. Core Timeout Implementation in `shell.py`

#### Option A: Thread-based timeout with concurrent.futures (Recommended)
```python
import concurrent.futures
from typing import Any, Callable

def _execute_with_timeout(self, code: str, timeout: int | None = None) -> Result:
    """Execute code with optional timeout using ThreadPoolExecutor."""
    
    if timeout is None:
        # No timeout - execute normally
        return self._execute_code(code)
    
    # Convert timeout from seconds to milliseconds if needed
    timeout_seconds = timeout / 1000 if timeout > 0 else timeout
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(self._execute_code, code)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError:
            # Cancel the future (though it may continue running)
            future.cancel()
            return self.save_result(
                ErrorResult(
                    code=code,
                    exception=TimeoutError(f"Code execution exceeded timeout of {timeout}ms"),
                    stdout="",
                    stderr="",
                )
            )
```

#### Option B: Async timeout with asyncio.timeout (Alternative)
```python
import asyncio

async def execute(self, code: str, timeout: int | None = None) -> Result:
    """Execute with asyncio timeout."""
    
    if timeout is None:
        return await sync_to_async(self._execute)(code)
    
    timeout_seconds = timeout / 1000 if timeout > 0 else timeout
    
    try:
        async with asyncio.timeout(timeout_seconds):
            return await sync_to_async(self._execute)(code)
    except asyncio.TimeoutError:
        return self.save_result(
            ErrorResult(
                code=code,
                exception=TimeoutError(f"Code execution exceeded timeout of {timeout}ms"),
                stdout="",
                stderr="",
            )
        )
```

### 2. Refactoring Plan

#### Step 1: Extract execution logic
- Move the actual code execution logic from `_execute` to a new method `_execute_code`
- This separation allows for cleaner timeout wrapping

#### Step 2: Implement timeout wrapper
- Modify `_execute` to use the timeout mechanism
- Handle timeout gracefully with clear error messages

#### Step 3: Update async wrapper
- Ensure the async `execute` method properly passes timeout to the sync method
- Consider whether timeout should be handled at async or sync level

### 3. Error Handling Enhancements

#### Create TimeoutResult or enhance ErrorResult
```python
@dataclass
class TimeoutResult:
    code: str
    timeout_ms: int
    stdout: str  # Partial output if any
    stderr: str  # Partial errors if any
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def output(self) -> str:
        return f"TimeoutError: Code execution exceeded {self.timeout_ms}ms timeout limit.\n\nPartial output:\n{self.stdout}"
```

Or simply use existing ErrorResult with a TimeoutError exception.

### 4. Testing Strategy

#### Test Cases to Add

1. **Basic timeout functionality**:
```python
async def test_execute_with_timeout_exceeded():
    """Test that long-running code times out."""
    shell = DjangoShell()
    code = "import time; time.sleep(5)"
    result = await shell.execute(code, timeout=1000)  # 1 second timeout
    
    assert isinstance(result, ErrorResult)
    assert "timeout" in result.output.lower()
```

2. **Normal execution with timeout specified**:
```python
async def test_execute_with_sufficient_timeout():
    """Test that fast code completes within timeout."""
    shell = DjangoShell()
    result = await shell.execute("2 + 2", timeout=5000)  # 5 seconds
    
    assert isinstance(result, ExpressionResult)
    assert result.value == 4
```

3. **Timeout with partial output**:
```python
async def test_timeout_with_partial_output():
    """Test that stdout captured before timeout is preserved."""
    shell = DjangoShell()
    code = """
print("Starting...")
import time
time.sleep(10)
print("This won't print")
"""
    result = await shell.execute(code, timeout=1000)
    
    assert isinstance(result, ErrorResult)
    assert "Starting..." in result.stdout
```

4. **State preservation after timeout**:
```python
async def test_state_after_timeout():
    """Test that shell state is consistent after timeout."""
    shell = DjangoShell()
    
    # Set a variable
    await shell.execute("x = 42")
    
    # Timeout on long operation
    await shell.execute("import time; time.sleep(10)", timeout=1000)
    
    # Variable should still be accessible
    result = await shell.execute("x")
    assert result.value == 42
```

5. **Edge cases**:
```python
async def test_zero_timeout():
    """Test behavior with zero or negative timeout."""
    shell = DjangoShell()
    result = await shell.execute("2 + 2", timeout=0)
    # Should either execute immediately or fail immediately
```

### 5. Documentation Updates

#### Tool Description Update
```python
@mcp.tool
async def django_shell(code: str, ctx: Context, timeout: int | None = None) -> str:
    """Execute Python code in a stateful Django shell session.
    
    ...existing description...
    
    Args:
        code: Python code to execute
        timeout: Optional execution timeout in milliseconds. Default is None (no timeout).
                Code that exceeds the timeout will be interrupted and a TimeoutError 
                will be returned. Note that some operations may not be interruptible.
    """
```

#### README Update
Add a section about timeout functionality:
- How to use it
- Limitations (some operations may not be interruptible)
- Best practices

### 6. Implementation Order

1. **Phase 1: Core Implementation**
   - Extract `_execute_code` method from `_execute`
   - Implement timeout wrapper using concurrent.futures
   - Update error handling for timeout cases

2. **Phase 2: Testing**
   - Add comprehensive timeout tests
   - Test edge cases and error conditions
   - Ensure backward compatibility

3. **Phase 3: Documentation**
   - Update docstrings
   - Update tool descriptions
   - Add examples to README

4. **Phase 4: Optimization (Optional)**
   - Consider caching ThreadPoolExecutor for performance
   - Add metrics/logging for timeout events
   - Consider making timeout configurable at server level

## Considerations and Trade-offs

### Pros of Thread-based Approach (Option A)
- Works well with synchronous Django ORM operations
- Clear separation between timeout and execution logic
- Can potentially interrupt blocking I/O operations

### Cons of Thread-based Approach
- Thread may continue running even after timeout
- Resource cleanup may be complex
- Not all operations are interruptible

### Pros of Async Approach (Option B)
- Native to async context
- Cleaner integration with FastMCP
- Better resource management

### Cons of Async Approach
- May not properly timeout synchronous operations in thread pool
- Could lead to confusing behavior with sync_to_async

## Recommendation

Use **Option A (Thread-based timeout)** because:
1. Django ORM operations are inherently synchronous
2. We're already using thread pools via `sync_to_async`
3. More predictable behavior for synchronous code
4. Better compatibility with existing Django ecosystem

## Migration Path

1. Add feature flag to enable/disable timeout (optional)
2. Implement with conservative default timeout (or None)
3. Add logging for timeout events
4. Monitor and adjust based on usage patterns

## Open Questions

1. Should timeout be in milliseconds or seconds? (Currently assumes milliseconds to match common conventions)
2. Should we have a server-level default timeout?
3. How should we handle cleanup of timed-out operations?
4. Should partial results be captured and returned?
5. Should we differentiate between soft and hard timeouts?

## Security Considerations

- Timeout prevents infinite loops and resource exhaustion
- Should document that malicious code could still spawn threads/processes
- Consider adding resource limits beyond just time

## Performance Impact

- Minimal overhead when timeout is None
- Small overhead for thread pool creation when timeout is specified
- Consider reusing thread pool for multiple executions

## Backward Compatibility

- Existing code without timeout parameter continues to work
- Default timeout=None preserves current behavior
- No breaking changes to API

## Future Enhancements

1. **Granular timeouts**: Different timeouts for different operations
2. **Resource limits**: Memory, CPU, I/O limits
3. **Cancellation tokens**: Allow graceful cancellation
4. **Progress reporting**: Report execution progress before timeout
5. **Retry logic**: Automatic retry with exponential backoff
