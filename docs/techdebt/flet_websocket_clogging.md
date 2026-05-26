# Technical Debt: Flet WebSocket Clogging under High Log Throughput

## 1. Real-Time Log Clogging
### Description
To output live build logs, `ModsView.execute_pipeline` reads the stdout of the compiler and calls `self.write_log()` on every line, which appends an `ft.Text` control to `log_view` and executes `page.update()`.
### Debt / Risk
* **WebSocket Bottlenecks:** During massive compilation phases (like initial shader compiles), Unreal Engine can print hundreds of log lines per second. Flooding the Flet local WebSocket server with hundreds of micro-updates per second can clog the channel, leading to UI lag, desynchronized progress bars, or memory leaks on the client webview.
* **Mitigation Needed:** In a production-grade refactor, logs should be buffered in a local thread-safe queue and flushed to the Flet UI in batches (e.g., every 100ms or 50 lines) rather than updating on every single line read.