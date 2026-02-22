"""
Base widget for processing operations with Worker pattern and progress tracking.

Provides a base class for all processing widgets with thread-safe operation
execution, progress dialog integration, and error/success message helpers.
"""

from typing import Any, Callable, Optional

from qtpy import QtCore, QtWidgets


class ProcessingWorker(QtCore.QObject):
    """
    Worker class for running processing operations in a separate thread.

    Extends the basic Worker pattern with progress signal support for
    long-running operations like staging, history building, or plotting.
    """
    finished = QtCore.Signal(object)
    progress = QtCore.Signal(int, int, str)  # current, total, message
    error = QtCore.Signal(str)

    def __init__(
        self,
        func: Callable,
        thread: QtCore.QThread = None,
        progress_callback: bool = False,
        **kwargs
    ):
        """
        Initialize the processing worker.

        Parameters
        ----------
        func : Callable
            The function to run in the background thread
        thread : QThread, optional
            Thread to move worker to. If provided, connections are set up automatically.
        progress_callback : bool
            If True, pass a progress callback function to func as 'progress_callback' kwarg
        **kwargs
            Additional keyword arguments to pass to func
        """
        super().__init__()
        self.func = func
        self.kwargs = kwargs
        self.progress_callback_enabled = progress_callback
        self._cancelled = False

        if thread is not None:
            self.moveToThread(thread)
            thread.started.connect(self.run)
            thread.finished.connect(self.deleteLater)
            thread.finished.connect(thread.deleteLater)
            self.finished.connect(thread.quit)

    def cancel(self):
        """Request cancellation of the operation."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancelled

    def _progress_callback(self, current: int, total: int, message: str = ""):
        """Internal callback for progress updates."""
        self.progress.emit(current, total, message)

    def run(self):
        """Execute the function and emit result or error."""
        try:
            if self.progress_callback_enabled:
                self.kwargs['progress_callback'] = self._progress_callback
            result = self.func(**self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(None)


class BaseProcessingWidget(QtWidgets.QWidget):
    """
    Base widget for all processing operations.

    Provides common functionality for running background operations with
    progress tracking, error handling, and user feedback.
    """

    # Signal emitted when an operation completes successfully
    operation_completed = QtCore.Signal(str, object)  # operation_name, result
    # Signal emitted when an operation fails
    operation_failed = QtCore.Signal(str, str)  # operation_name, error_message

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._active_threads: list[QtCore.QThread] = []
        self._active_workers: list[ProcessingWorker] = []
        self._progress_dialog: Optional[QtWidgets.QProgressDialog] = None

    def run_operation(
        self,
        name: str,
        func: Callable,
        on_complete: Optional[Callable[[object], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        show_progress: bool = True,
        progress_title: str = "Processing...",
        cancellable: bool = True,
        use_progress_callback: bool = False,
        **kwargs
    ):
        """
        Run a long-running operation in a background thread.

        Parameters
        ----------
        name : str
            Name of the operation (for logging and signals)
        func : Callable
            The function to execute
        on_complete : Callable, optional
            Callback when operation completes successfully
        on_error : Callable, optional
            Callback when operation fails
        show_progress : bool
            If True, show a progress dialog
        progress_title : str
            Title for the progress dialog
        cancellable : bool
            If True, show cancel button on progress dialog
        use_progress_callback : bool
            If True, pass progress_callback to func for detailed progress updates
        **kwargs
            Arguments to pass to func
        """
        thread = QtCore.QThread(parent=self)
        worker = ProcessingWorker(
            func,
            thread,
            progress_callback=use_progress_callback,
            **kwargs
        )

        self._active_threads.append(thread)
        self._active_workers.append(worker)

        # Set up progress dialog
        if show_progress:
            self._progress_dialog = QtWidgets.QProgressDialog(
                f"Running {name}...",
                "Cancel" if cancellable else None,
                0, 0,
                self
            )
            self._progress_dialog.setWindowTitle(progress_title)
            self._progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
            self._progress_dialog.setMinimumDuration(0)

            if cancellable:
                self._progress_dialog.canceled.connect(worker.cancel)

            # Connect progress signal for detailed updates
            if use_progress_callback:
                worker.progress.connect(self._update_progress)

            self._progress_dialog.show()

        def handle_finished(result):
            self._cleanup_operation(thread, worker)
            if self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog = None
            if result is not None:
                self.operation_completed.emit(name, result)
                if on_complete:
                    on_complete(result)

        def handle_error(error_msg):
            self._cleanup_operation(thread, worker)
            if self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog = None
            self.operation_failed.emit(name, error_msg)
            if on_error:
                on_error(error_msg)
            else:
                self.show_error(f"Operation '{name}' failed:\n{error_msg}")

        worker.finished.connect(handle_finished)
        worker.error.connect(handle_error)

        thread.start()

    def _update_progress(self, current: int, total: int, message: str = ""):
        """Update the progress dialog with detailed progress."""
        if self._progress_dialog:
            if total > 0:
                self._progress_dialog.setMaximum(total)
                self._progress_dialog.setValue(current)
            if message:
                self._progress_dialog.setLabelText(message)

    def _cleanup_operation(self, thread: QtCore.QThread, worker: ProcessingWorker):
        """Clean up after an operation completes."""
        if thread in self._active_threads:
            self._active_threads.remove(thread)
        if worker in self._active_workers:
            self._active_workers.remove(worker)

    def show_error(self, message: str, title: str = "Error"):
        """Show an error message dialog."""
        QtWidgets.QMessageBox.critical(self, title, message)

    def show_success(self, message: str, title: str = "Success"):
        """Show a success message dialog."""
        QtWidgets.QMessageBox.information(self, title, message)

    def show_warning(self, message: str, title: str = "Warning"):
        """Show a warning message dialog."""
        QtWidgets.QMessageBox.warning(self, title, message)

    def ask_confirmation(self, message: str, title: str = "Confirm") -> bool:
        """Ask the user for confirmation and return True if accepted."""
        reply = QtWidgets.QMessageBox.question(
            self, title, message,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        return reply == QtWidgets.QMessageBox.StandardButton.Yes

    def cancel_all_operations(self):
        """Cancel all running operations."""
        for worker in self._active_workers:
            worker.cancel()

    def closeEvent(self, event):
        """Ensure all threads are stopped when widget closes."""
        self.cancel_all_operations()
        for thread in self._active_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)  # Wait up to 1 second
        super().closeEvent(event)
