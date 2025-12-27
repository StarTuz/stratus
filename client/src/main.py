#!/usr/bin/env python3
"""
SayIntentionsML - Native Mac/Linux Client

Main entry point for the application.

Usage:
    python main.py           # Launch GUI
    python main.py --cli     # Launch CLI mode
    python main.py --help    # Show help
"""

import sys
import os
import argparse
import logging

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description='SayIntentionsML - Native Mac/Linux Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
    Default (no args)    Launch the GUI application
    --cli                Launch interactive command-line interface
    
For CLI-only usage, see: python cli.py --help
"""
    )
    
    parser.add_argument('--cli', action='store_true',
                        help='Launch in CLI mode instead of GUI')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.cli:
        # Launch CLI
        from cli import SayIntentionsCLI
        cli = SayIntentionsCLI()
        cli.cmdloop()
    else:
        # Check for plugin installation before starting GUI
        try:
            from core.sim_installer import check_and_install
            check_and_install()
        except Exception as e:
            logging.error(f"Failed to run auto-installer: {e}")
            
        # Launch GUI
        from ui import run_gui
        run_gui()


if __name__ == "__main__":
    main()
