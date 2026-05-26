# UI Philosophy

The UI is built using Flet (0.85+) and strictly adheres to modern Flet constraints regarding state management and component mounting.

## View Wrapper Pattern
Flet uses C++ bindings that override Python's `__getattr__` and `__setattr__`. Subclassing Flet controls (e.g., `class ModItem(ft.Container)`) and adding custom methods can lead to runtime `AttributeError` exceptions when the framework attempts to map the custom methods to the C++ layout engine.

To bypass this, components (`ModsView`, `SettingsView`, `ModItem`) are built as standard Python classes that do not inherit from Flet types. The fully constructed Flet control tree is stored inside an instance attribute (e.g., `self.view`), which is then appended to the page.

## In-Memory Filtering
To prevent disk I/O bottlenecks, directory scanning (`utils.scanner.get_mod_info`) occurs only when explicitly clicking "Refresh" or immediately after a build operation completes.

The `ModsView` class maintains `self.cached_items`, a list of constructed `ModItem` objects. Filtering by name, tag, or status iterates over this list in memory, updating the UI list instantly.

## Unmounted Control Protection
Flet throws a `RuntimeError` if `.update()` is called on a control that is not currently mounted on the page layout. To prevent crashes during background builds when a user filters the active item out of view, all asynchronous UI updates check if the control is mounted:
```python
if self.view.page:
    try:
        self.view.update()
    except Exception:
        pass
```