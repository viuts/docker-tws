#!/usr/bin/env python3

import binascii
import configparser
import glob
import os
import pwd
import shutil
import subprocess
import time


def fix_permissions_and_restart():
    subprocess.check_call(['chown', '-R', 'tws:', '/home/tws'])
    os.execlp('runuser', 'runuser', '-p', 'tws', 'bash', '-c', __file__)


def set_timezone():
    os.environ.setdefault('TZ', 'America/New_York')


def get_profile_dir():
    parser = configparser.ConfigParser()
    with open('/conf/jts.ini') as fp:
        parser.read_file(fp)

    d = dict(parser.items('Logon'))
    print(d)
    lst = d['usernametodirectory'].split(',')
    print('Found profile directory:', lst[0])
    return lst[0]


def get_tws_version():
    paths = glob.glob(os.path.expanduser('~/Jts/ibgateway/???'))
    version = os.path.basename(paths[0])
    print('Found TWS version:', version)
    return version


def set_vnc_password():
    default_password = binascii.hexlify(os.getrandom(16)).decode()
    os.environ.setdefault('VNC_PASSWORD', default_password)

    os.makedirs(os.path.expanduser('~/.vnc'), exist_ok=True)
    with open(os.path.expanduser('~/.vnc/passwd'), 'w') as fp:
        proc = subprocess.Popen(
            args=['vncpasswd', '-f'],
            stdout=fp,
            stdin=subprocess.PIPE,
        )
        proc.communicate(input=os.environ['VNC_PASSWORD'].encode())
        proc.wait()
        assert proc.returncode == 0

    subprocess.check_call(['chmod', '-R', 'go=', os.path.expanduser('~/.vnc')])
    print('VNC password is:', os.environ['VNC_PASSWORD'])


def copy_initial_data():
    if os.path.exists('/conf/jts.ini'):
        shutil.copy('/conf/jts.ini',
                    os.path.expanduser('~/Jts/jts.ini'))

    if os.path.exists('/conf/tws.xml'):
        profile_dir = os.path.join('~/Jts', get_profile_dir())
        os.makedirs(os.path.expanduser(profile_dir), exist_ok=True)
        shutil.copy('/conf/tws.xml',
                    os.path.expanduser(os.path.join(profile_dir, 'tws.xml')))


def write_ibc_config():
    os.makedirs(os.path.expanduser('~/ibc'), exist_ok=True)
    env = lambda k, d: (os.environ.get(k, d),)

    with open(os.path.expanduser('~/ibc/config.ini'), 'w') as fp:
        fp.write('%s\n' % (
            '\n'.join((
                'FIX=%s' % env('IBC_FIX', 'no'),
                'IbLoginId=%s' % env(
                    'IBC_USERNAME',
                    '',
                ),
                'IbPassword=%s' % env(
                    'IBC_PASSWORD',
                    '',
                ),
                'FIXLoginId=%s' % env(
                    'IBC_FIX_USERNAME',
                    '',
                ),
                'FIXPassword=%s' % env(
                    'IBC_FIX_PASSWORD',
                    '',
                ),
                'TradingMode=%s' % env(
                    'IBC_TRADING_MODE',
                    'live',
                ),
                'IbDir=',
                'SendTWSLogsToConsole=%s' % env(
                    'IBC_SEND_TWS_LOGS_TO_CONSOLE',
                    'yes',
                ),
                'StoreSettingsOnServer=%s' % env(
                    'IBC_STORE_SETTINGS_ON_SERVER',
                    'no',
                ),
                'MinimizeMainWindow=%s' % env(
                    'IBC_MINIMIZE_MAIN_WINDOW',
                    'no',
                ),
                'MaximizeMainWindow=%s' % env(
                    'IBC_MAXIMIZE_MAIN_WINDOW',
                    'yes'
                ),
                'ExistingSessionDetectedAction=%s' % env(
                    'IBC_EXISTING_SESSION_DETECTED',
                    'manual',
                ),
                'AcceptIncomingConnectionAction=%s' % env(
                    'IBC_ACCEPT_INCOMING_CONNECTION',
                    'accept',
                ),
                'ShowAllTrades=%s' % env(
                    'IBC_SHOW_ALL_TRADES',
                    'no',
                ),
                'OverrideTwsApiPort=',
                'ReadOnlyLogin=%s' % env(
                    'IBC_READONLY_LOGIN',
                    'no',
                ),
                'ReadOnlyApi=%s' % env(
                    'IBC_READONLY_API',
                    '',
                ),
                'AcceptNonBrokerageAccountWarning=%s' % env(
                    'IBC_ACCEPT_NON_BROKERAGE_WARNING',
                    'yes',
                ),
                'IbAutoClosedown=%s' % env(
                    'IBC_AUTO_CLOSEDOWN',
                    'yes',
                ),
                'ClosedownAt=%s' % env(
                    'IBC_CLOSEDOWN_AT',
                    ''
                ),
                'AllowBlindTrading=%s' % env(
                    'IBC_ALLOW_BLIND_TRADING',
                    'no',
                ),
                'DismissPasswordExpiryWarning=%s' % env(
                    'IBC_DISMISS_PASSWORD_EXPIRY',
                    'no',
                ),
                'DismissNSEComplianceNotice=%s' % env(
                    'IBC_DISMISS_NSE_COMPLIANCE',
                    'yes',
                ),
                'SaveTwsSettingsAt=',
                'CommandServerPort=7462',
                'ControlFrom=%s' % env(
                    'IBC_CONTROL_FROM',
                    '172.17.0.1',
                ),
                'BindAddress=',
                'CommandPrompt=%s' % env(
                    'IBC_COMMAND_PROMPT',
                    'IBC> ',
                ),
                'SuppressInfoMessages=%s' % env(
                    'IBC_SUPPRESS_INFO_MESSAGES',
                    'yes'
                ),
                'LogComponents=%s' % env(
                    'IBC_LOG_COMPONENTS',
                    'never',
                ),
            )),
        ))


def fixup_environment():
    pwent = pwd.getpwuid(os.geteuid())
    os.environ['USER'] = pwent.pw_name
    os.environ['LOGNAME'] = pwent.pw_name
    os.environ['HOME'] = pwent.pw_dir
    os.environ['SHELL'] = pwent.pw_shell


def cleanup_x11():
    try:
        os.unlink('/tmp/.X11-unix/X0')
    except OSError:
        pass

    try:
        os.unlink('/tmp/.X0-lock')
    except OSError:
        pass


def start_vnc_server():
    vnc = subprocess.Popen([
        'Xtightvnc',
        ':0',
        '-geometry', os.environ.get('VNC_GEOMETRY', '1920x1080'),
        '-depth', os.environ.get('VNC_DEPTH', '24'),
        '-rfbwait', '120000',
        '-rfbauth', os.path.expanduser('~/.vnc/passwd'),
        '-desktop', os.environ.get(
            'VNC_NAME',
            'tws-%s-%s' % (
                os.environ.get('IBC_TRADING_MODE', 'live'),
                os.environ.get('IBC_USERNAME', 'default')
            ),
        ),
    ])

    while not os.path.exists('/tmp/.X11-unix/X0'):
        if vnc.poll():
            print('VNC failed to start')
            return False
        time.sleep(0.05)

    return True


def update_jvm_options():
    path = '/home/tws/Jts/ibgateway/%s/ibgateway.vmoptions' % (get_tws_version(),)

    with open(path, 'r+') as fp:
        lines = fp.readlines()
        print(lines)
        for i, line in enumerate(lines):
            if line.startswith('-Xmx'):
                continue # skip if
                # lines[i] = '-Xmx%s\n' % (os.environ.get('JVM_HEAP_SIZE', '4096m'),)

        lines.append('-XX:+UnlockExperimentalVMOptions\n')
        lines.append('-XX:+UseCGroupMemoryLimitForHeap\n')
        lines.append('-XX:InitialRAMFraction=4\n')
        lines.append('-XX:MaxRAMFraction=2\n')

        fp.seek(0)
        fp.truncate(0)
        fp.writelines(lines)


def start_tws():
    os.environ['DISPLAY'] = ':0'

    subprocess.check_call([
        'xsetroot',
        '-solid', os.environ.get('X11_ROOT_COLOR', '#473C8B')
    ])

    wm = subprocess.Popen(['openbox'])
    os.execl('/opt/ibc/scripts/ibcstart.sh',
             '/opt/ibc/scripts/ibcstart.sh',
             '-g',
             get_tws_version())


def main():
    if os.geteuid() == 0:
        fix_permissions_and_restart()

    fixup_environment()
    set_timezone()
    set_vnc_password()
    cleanup_x11()
    copy_initial_data()
    write_ibc_config()
    update_jvm_options()
    if not start_vnc_server():
        return
    start_tws()


if __name__ == '__main__':
    main()
