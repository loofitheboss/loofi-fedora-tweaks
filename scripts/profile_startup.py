#!/usr/bin/env python3
"""Profile application startup time.

Usage:
    python scripts/profile_startup.py [gui|cli]

Output:
    Prints top 50 slowest functions sorted by cumulative time.
"""
import argparse
import cProfile
import pstats
import sys
import os

# Add loofi-fedora-tweaks to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'loofi-fedora-tweaks'))


def profile_gui_startup():
    """Profile GUI main window initialization."""
    from PyQt6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication([])

    profiler = cProfile.Profile()
    profiler.enable()

    window = MainWindow()
    window.show()

    profiler.disable()

    # Print statistics
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')

    print("\n" + "=" * 80)
    print("GUI STARTUP PROFILING RESULTS")
    print("=" * 80)
    print("\nTop 50 functions by cumulative time:\n")

    stats.print_stats(50)

    # Calculate total time
    total_time = sum(stat[3] for stat in stats.stats.values())
    print(f"\nTotal startup time: {total_time:.3f} seconds")


def profile_cli_startup():
    """Profile CLI initialization."""
    from cli.main import main

    profiler = cProfile.Profile()
    profiler.enable()

    # Run version check (lightweight operation)
    sys.argv = ['loofi-fedora-tweaks', '--version']
    try:
        main()
    except SystemExit:
        pass

    profiler.disable()

    # Print statistics
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')

    print("\n" + "=" * 80)
    print("CLI STARTUP PROFILING RESULTS")
    print("=" * 80)
    print("\nTop 50 functions by cumulative time:\n")

    stats.print_stats(50)

    # Calculate total time
    total_time = sum(stat[3] for stat in stats.stats.values())
    print(f"\nTotal startup time: {total_time:.3f} seconds")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Profile application startup')
    parser.add_argument(
        'mode',
        nargs='?',
        default='gui',
        choices=['gui', 'cli'],
        help='Profile GUI or CLI startup (default: gui)'
    )

    args = parser.parse_args()

    if args.mode == 'gui':
        print("Profiling GUI startup...")
        profile_gui_startup()
    else:
        print("Profiling CLI startup...")
        profile_cli_startup()


if __name__ == '__main__':
    main()
