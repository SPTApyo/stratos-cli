import sys
import argparse
from stratos.ui.dashboard import main
from stratos.utils.config import load_config, save_config
from stratos import __version__

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Stratos CLI - Multi-Agent Autonomous Coding System",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Examples:
  stratos
  stratos -p MyProject -d 'Create a snake game'
  stratos --debug"""
    )
    
    parser.add_argument("-v", "--version", action="version", version=f"Stratos CLI v{__version__}")
    
    # Project Launch Args
    parser.add_argument("-p", "--project", metavar="NAME", help="Directly launch a specific project by name")
    parser.add_argument("-d", "--desc", metavar="TEXT", help="Description for the project (requires -p)")
    parser.add_argument("--quick", action="store_true", help="Quick launch MVP mode (equivalent to -p *)")
    
    # Configuration Overrides
    parser.add_argument("--debug", action="store_true", help="Enable debug mode logging")
    parser.add_argument("--no-thoughts", action="store_true", help="Hide agent thought process (cleaner UI)")
    parser.add_argument("--theme", metavar="NAME", help="Override UI theme (e.g. 'dracula_dark')")
    parser.add_argument("--reset-config", action="store_true", help="Reset configuration to defaults")
    
    # Advanced
    parser.add_argument("--api-key", metavar="KEY", help="Override Gemini API Key for this session")

    return parser.parse_args()

def main_entry():
    args = parse_arguments()
    
    # Apply configuration resets first
    if args.reset_config:
        from stratos.utils.config import DEFAULT_CONFIG
        save_config(DEFAULT_CONFIG)
        print("Configuration reset to defaults.")
        sys.exit(0)
        
    try:
        main(args)
    except KeyboardInterrupt:
        print("\n\n  › STRATOS | User interruption. Closing...")
        sys.exit(0)

if __name__ == "__main__":
    main_entry()
