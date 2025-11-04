import sys
import os
from datetime import datetime
from pathlib import Path

class TerminalLogger:
    """
    Captures all terminal output (stdout and stderr) and saves to a log file.
    Maintains last 10 runs with clear separation.
    """
    
    MAX_RUNS = 10  # Maximum number of runs to keep in the log file
    
    def __init__(self, log_dir="data", log_filename="terminal_log.txt"):
        """
        Initialize the terminal logger.
        
        Args:
            log_dir: Directory to store log files (relative to executable/script)
            log_filename: Name of the log file
        """
        # Determine base directory
        if getattr(sys, 'frozen', False):
            # Running as exe - save in _internal/data directory
            self.base_dir = Path(sys.executable).parent / "_internal"
        else:
            # Running as script - go to project root
            # terminal_logger.py is in src/frontend/, so go up 2 levels to reach project root
            self.base_dir = Path(__file__).resolve().parent.parent.parent
        
        print(f"[DEBUG] Terminal Logger Base Directory: {self.base_dir}")
        
        # Create log directory
        self.log_dir = self.base_dir / log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[DEBUG] Log Directory: {self.log_dir}")
        
        # Create log file path
        self.log_file = self.log_dir / log_filename
        
        print(f"[DEBUG] Log File Path: {self.log_file}")
        
        # Store original stdout and stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Initialize log file (rotate old runs if needed)
        self._initialize_log_file()
        
        # Create custom writer
        self.log_writer = LogWriter(self.log_file, self.original_stdout)
        self.error_writer = LogWriter(self.log_file, self.original_stderr, is_error=True)
        
    def _count_existing_runs(self, content: str) -> int:
        """Count the number of existing runs in the log file"""
        # Count occurrences of "Session Started:" which marks the beginning of each run
        return content.count("Session Started:")
    
    def _trim_old_runs(self, content: str) -> str:
        """
        Trim the log content to keep only the last (MAX_RUNS - 1) runs.
        This makes room for the new run.
        """
        runs = []
        current_run = []
        
        for line in content.split('\n'):
            if "Session Started:" in line and current_run:
                # Save the previous run
                runs.append('\n'.join(current_run))
                current_run = [line]
            else:
                current_run.append(line)
        
        # Add the last run
        if current_run:
            runs.append('\n'.join(current_run))
        
        # Keep only the last (MAX_RUNS - 1) runs
        if len(runs) > self.MAX_RUNS - 1:
            runs = runs[-(self.MAX_RUNS - 1):]
        
        return '\n'.join(runs)
    
    def _initialize_log_file(self):
        """Initialize log file and maintain last 10 runs"""
        try:
            existing_content = ""
            
            # Read existing content if file exists
            if self.log_file.exists():
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                
                # Count existing runs
                run_count = self._count_existing_runs(existing_content)
                print(f"[DEBUG] Found {run_count} existing run(s) in log file")
                
                # If we have MAX_RUNS or more, trim to keep only (MAX_RUNS - 1)
                if run_count >= self.MAX_RUNS:
                    existing_content = self._trim_old_runs(existing_content)
                    print(f"[DEBUG] Trimmed log file to keep last {self.MAX_RUNS - 1} runs")
            
            # Write the file with existing content (if any) plus new header
            with open(self.log_file, 'w', encoding='utf-8') as f:
                # Write existing content first (if any)
                if existing_content.strip():
                    f.write(existing_content)
                    # Add separation between runs
                    if not existing_content.endswith('\n'):
                        f.write('\n')
                    f.write('\n' + '=' * 80 + '\n')
                    f.write('=' * 80 + '\n\n')
                
                # Write new run header
                f.write("=" * 80 + "\n")
                f.write(f"GeoCoPilot Application Log - Run #{self._count_existing_runs(existing_content) + 1}\n")
                f.write(f"Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Log File: {self.log_file}\n")
                f.write("=" * 80 + "\n\n")
                f.flush()  # Force write to disk
            
            print(f"[DEBUG] Log file initialized successfully at: {self.log_file}")
        except Exception as e:
            print(f"Warning: Could not initialize log file: {e}", file=self.original_stderr)
    
    def start(self):
        """Start capturing terminal output"""
        sys.stdout = self.log_writer
        sys.stderr = self.error_writer
        print(f"Terminal logging started. Log file: {self.log_file}")
        
    def stop(self):
        """Stop capturing and restore original stdout/stderr"""
        if sys.stdout == self.log_writer:
            sys.stdout = self.original_stdout
        if sys.stderr == self.error_writer:
            sys.stderr = self.original_stderr
        
        # Write footer
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"Session Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n")
                f.flush()  # Force write to disk
            print(f"[DEBUG] Log footer written successfully", file=self.original_stdout)
        except Exception as e:
            print(f"Warning: Could not write log footer: {e}", file=self.original_stderr)
    
    def get_log_path(self):
        """Return the full path to the log file"""
        return str(self.log_file)


class LogWriter:
    """Custom writer that duplicates output to both console and log file"""
    
    def __init__(self, log_file, original_stream, is_error=False):
        self.log_file = log_file
        self.original_stream = original_stream
        self.is_error = is_error
        
    def write(self, message):
        """Write to both console and log file"""
        # Write to original console
        try:
            self.original_stream.write(message)
            self.original_stream.flush()
        except Exception:
            pass  # Silently fail if console write fails
        
        # Write to log file with timestamp for non-empty messages
        if message.strip():
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    prefix = "[ERROR] " if self.is_error else "[INFO]  "
                    f.write(f"{timestamp} {prefix}{message}")
                    if not message.endswith('\n'):
                        f.write('\n')
                    f.flush()  # Force write to disk immediately
            except Exception as e:
                # Only print error to original stream if it's critical
                try:
                    self.original_stream.write(f"[LOG ERROR] {e}\n")
                except Exception:
                    pass  # Give up silently
    
    def flush(self):
        """Flush both streams"""
        try:
            self.original_stream.flush()
        except Exception:
            pass
    
    def isatty(self):
        """Check if the original stream is a terminal"""
        return hasattr(self.original_stream, 'isatty') and self.original_stream.isatty()


# Example usage function
def setup_terminal_logging():
    """
    Setup function to initialize terminal logging.
    Call this at the very beginning of your main() function.
    """
    logger = TerminalLogger(log_dir="data", log_filename="terminal_log.txt")
    logger.start()
    return logger